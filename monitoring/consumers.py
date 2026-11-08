import json
import time
from urllib.parse import parse_qs

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.utils import timezone

from accounts.utils import get_user_from_token_payload
from core.application_logger import ApplicationLogger
from core.responses import get_form_errors
from .forms import LiveActionForm
from .services import (
    authenticate_live_token,
    build_event,
    current_quote,
    groups_for_user,
    ticker_group,
    timestamp_to_iso,
    to_iso,
)

CLOSE_UNAUTHORIZED = 4401
MAX_SUBSCRIBED_TICKERS = 20


class LiveConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.user = None
        self.joined_groups = []
        self.tickers = []
        self.accept()

        payload, user = authenticate_live_token(self.get_token())

        if user is None:
            ApplicationLogger.warning("Live connection rejected: invalid or expired token.")
            self.close_session("Invalid or expired token. Refresh the token and reconnect.")
            return

        self.user = user
        self.payload = payload
        self.role = user.role
        self.expires_at = payload["exp"]

        for group in groups_for_user(user):
            self.join_group(group)

        ApplicationLogger.info(f"Live connection opened: username={user.username}, role={user.role}")
        data = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "token_expires_at": timestamp_to_iso(self.expires_at),
            "max_tickers": MAX_SUBSCRIBED_TICKERS,
        }
        self.send_json(build_event("connection.ready", "Connected to live risk monitoring.", data))

    def disconnect(self, code):
        for group in self.joined_groups:
            async_to_sync(self.channel_layer.group_discard)(group, self.channel_name)

        if self.user is not None:
            ApplicationLogger.info(f"Live connection closed: username={self.user.username}, code={code}")

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            content = json.loads(text_data or "")
        except json.JSONDecodeError:
            self.send_error("Messages must be valid JSON.", {"message": ["Send a JSON object with an action."]})
            return

        self.receive_json(content)

    def receive_json(self, content, **kwargs):
        if not self.session_is_valid():
            return

        if not isinstance(content, dict):
            self.send_error("Message rejected.", {"action": ["This field is required."]})
            return

        form = LiveActionForm(content)

        if not form.is_valid():
            self.send_error("Message rejected.", get_form_errors(form))
            return

        action = form.cleaned_data["action"]
        tickers = form.cleaned_data["tickers"]

        if action == "subscribe":
            self.subscribe(tickers)
        elif action == "unsubscribe":
            self.unsubscribe(tickers)
        else:
            self.pong()

    def live_event(self, message):
        if self.session_is_valid():
            self.send_json(message["event"])

    def get_token(self):
        query = parse_qs(self.scope["query_string"].decode())
        return query.get("token", [""])[0]

    def join_group(self, group):
        async_to_sync(self.channel_layer.group_add)(group, self.channel_name)
        self.joined_groups.append(group)

    def leave_group(self, group):
        async_to_sync(self.channel_layer.group_discard)(group, self.channel_name)
        self.joined_groups.remove(group)

    def session_is_valid(self):
        if self.user is None:
            return False

        if time.time() >= self.expires_at:
            ApplicationLogger.info(f"Live connection token expired: username={self.user.username}")
            self.close_session("Access token expired. Refresh the token and reconnect.")
            return False

        return True

    def close_session(self, message):
        self.user = None
        self.send_json(build_event("error", message, errors={"token": [message]}))
        self.close(code=CLOSE_UNAUTHORIZED)

    def send_error(self, message, errors):
        self.send_json(build_event("error", message, errors=errors))

    def subscribe(self, tickers):
        new_tickers = [ticker for ticker in tickers if ticker not in self.tickers]

        if len(self.tickers) + len(new_tickers) > MAX_SUBSCRIBED_TICKERS:
            message = f"You can follow at most {MAX_SUBSCRIBED_TICKERS} tickers at once."
            self.send_error(message, {"tickers": [message]})
            return

        for ticker in new_tickers:
            self.join_group(ticker_group(ticker))
            self.tickers.append(ticker)

        self.send_json(build_event("subscribed", "Following live prices.", {"tickers": self.tickers}))

        for ticker in new_tickers:
            quote = current_quote(ticker)

            if quote is not None:
                self.send_json(build_event("price.update", f"Latest price for {ticker}.", quote))

    def unsubscribe(self, tickers):
        for ticker in tickers:
            if ticker in self.tickers:
                self.leave_group(ticker_group(ticker))
                self.tickers.remove(ticker)

        self.send_json(build_event("unsubscribed", "Stopped following those tickers.", {"tickers": self.tickers}))

    def pong(self):
        user = get_user_from_token_payload(self.payload)

        if user is None or user.role != self.role:
            ApplicationLogger.warning(f"Live session ended after account change: username={self.user.username}")
            self.close_session("Your account changed. Log in again and reconnect.")
            return

        data = {
            "server_time": to_iso(timezone.now()),
            "token_expires_at": timestamp_to_iso(self.expires_at),
        }
        self.send_json(build_event("pong", "Connection is alive.", data))