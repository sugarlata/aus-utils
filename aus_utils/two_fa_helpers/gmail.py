import imaplib
import email
import email.policy
import email.message

from loguru import logger

from aus_utils.exceptions import TwoFAException


class Gmail2FA:
    """Class to handle Gmail 2FA email retrieval and archiving."""

    def __init__(
        self,
        username: str,
        password: str,
        imap_server: str = "imap.gmail.com",
    ):
        """Initialize the Gmail2FA class.

        Args:
            username (str): Gmail username.
            password (str): Gmail password.
            imap_server (str): IMAP server address. Defaults to "imap.gmail.com".
        """
        self._imap_server = imap_server
        self._username = username
        self._password = password

    def _connect(self) -> None:
        """Connect to the Gmail IMAP server and log in.

        Raises:
            TwoFAException: If the login fails.
        """

        logger.debug("Connecting to Gmail IMAP server")
        self._mail = imaplib.IMAP4_SSL(self._imap_server)
        status, message = self._mail.login(self._username, self._password)

        if status != "OK":
            raise TwoFAException(f"Login failed: {message}")

        logger.info(f"Login status: {status}, message: {message}")

    def _disconnect(self) -> None:
        """Disconnect from the Gmail IMAP server."""
        try:
            self._mail.logout()
            logger.debug("Disconnected from Gmail IMAP server")
        except Exception as e:
            logger.error(f"Error during logout: {e}")

    def get_messages(
        self, substring_sender_filter: str | None = None, message_limit: int = 5
    ) -> list[tuple[str, email.message.EmailMessage]]:
        """Retrieve the latest messages from the Gmail inbox.

        Args:
            message_limit (int): The number of messages to retrieve. Defaults to 5.

        Returns:
            list[tuple[str, email.message.EmailMessage]]: A list of tuples containing message UIDs and email messages.
        """

        try:
            self._connect()
            message_list = self._get_uid_list()

            if substring_sender_filter:
                return [
                    x
                    for x in self._download_messages(message_list[-message_limit:])
                    if substring_sender_filter in x[1]["from"]
                ]

            else:
                return self._download_messages(message_list[-message_limit:])

        finally:
            self._disconnect()

    def _get_uid_list(self) -> list[str]:
        """Fetch the list of message IDs from the Gmail inbox.

        Returns:
            list[str]: A list of message IDs.
        Raises:
            TwoFAException: If fetching messages fails.
        """

        logger.debug("Fetching messages from inbox")
        self._mail.select("inbox")
        status: str
        messages: list[str]
        status, messages = self._mail.uid("SEARCH", None, "ALL")  # type: ignore[arg-type]

        if status != "OK":
            raise TwoFAException("Failed to fetch messages")

        return messages[0].split()

    def _download_messages(
        self, email_uid_list: list[str]
    ) -> list[tuple[str, email.message.EmailMessage]]:
        """Download the email messages for the given list of message IDs.

        Args:
            email_id_list (list[str]): A list of message IDs to download.

        Returns:
            list[tuple[str, email.message.EmailMessage]]: A list of tuples containing message IDs and email messages.

        """

        email_message_list = []
        for email_uid in email_uid_list:
            logger.debug(f"Fetching message ID: {email_uid}")
            status, message_data = self._mail.uid("FETCH", email_uid, "(RFC822)")

            if status != "OK":
                logger.error(f"Failed to fetch message {email_uid}")
                continue

            email_message: email.message.EmailMessage = email.message_from_bytes(
                message_data[0][1], policy=email.policy.default
            )
            email_message_list.append((email_uid, email_message))

        return email_message_list

    def _archive_message(self, email_uid: str) -> None:
        """Archive a specific email message by its ID.

        Args:
            email_id (str): The ID of the email message to archive.
            email_content_hash (str): The SHA256 hash of the email content to validate before archiving.

        Raises:
            TwoFAException: If the message cannot be validated or archived.
        """

        try:
            logger.debug(f"Archiving message UID: {email_uid}")

            # Gmail Archiving can be done by an IMAP call to delete
            self._mail.select("inbox")

            self._mail.uid("STORE", email_uid, "+FLAGS", "\\Deleted")
            self._mail.expunge()

        except Exception as e:
            logger.error(f"Failed to archive message {email_uid}: {e}")

    def archive_message(self, email_id: str) -> None:
        """Archive a specific email message by its ID.

        Args:
            email_id (str): The ID of the email message to archive.

        Raises:
            TwoFAException: If the message cannot be archived.
        """

        try:
            self._connect()
            self._archive_message(email_id)

        finally:
            self._disconnect()
