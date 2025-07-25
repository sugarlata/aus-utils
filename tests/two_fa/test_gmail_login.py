import pytest

from aus_utils.exceptions import TwoFAException
from aus_utils.two_fa_helpers.gmail import Gmail2FA


@pytest.fixture
def mock_imap(mocker):
    mock = mocker.patch("imaplib.IMAP4_SSL", autospec=True)
    instance = mock.return_value
    instance.login.return_value = ("OK", [b"Logged in"])
    instance.logout.return_value = ("BYE", [b"Logged out"])

    return instance


def test_get_messages_returns_emails(mock_imap):
    mock_imap.select.return_value = ("OK", [b""])
    mock_imap.uid.side_effect = [
        ("OK", [b"1 2"]),  # SEARCH response
        ("OK", [(None, b"Subject: test\nFrom: test@example.com\n\nBody")]),
        ("OK", [(None, b"Subject: test2\nFrom: test2@example.com\n\nBody2")]),
    ]

    gmail = Gmail2FA("user", "pass")
    messages = gmail.get_messages()

    assert len(messages) == 2
    assert messages[0][0] == b"1"


def test_login_failure_raises(mocker):
    mock = mocker.patch("imaplib.IMAP4_SSL", autospec=True)
    instance = mock.return_value
    instance.login.return_value = ("NO", [b"Invalid credentials"])

    gmail = Gmail2FA("user", "wrongpass")
    with pytest.raises(TwoFAException):
        gmail.get_messages()


def test_archive_message(mock_imap):
    mock_imap.select.return_value = ("OK", [b""])
    mock_imap.uid.return_value = ("OK", [b""])
    mock_imap.expunge.return_value = ("OK", [])

    gmail = Gmail2FA("user", "pass")
    gmail.archive_message("1")

    mock_imap.uid.assert_called_with("STORE", "1", "+FLAGS", "\\Deleted")


def test_get_messages_filtered_by_sender(mock_imap):
    mock_imap.select.return_value = ("OK", [b""])
    mock_imap.uid.side_effect = [
        ("OK", [b"1"]),  # SEARCH
        ("OK", [(None, b"Subject: x\nFrom: match@example.com\n\nTest")]),
    ]

    gmail = Gmail2FA("user", "pass")
    msgs = gmail.get_messages(substring_sender_filter="match")
    assert len(msgs) == 1
