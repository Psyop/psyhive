"""Tools relating to email."""

import os
import smtplib

from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

import six

_FROM_EMAIL = '{}@psyop.tv'.format(os.environ.get('USERNAME'))
_PSYOP_EMAIL_SERVER = "smtp.psyop.tv"


def send_email(to_, subject, body, from_=_FROM_EMAIL, html=False):
    """Send an email.

    Args:
        to_ (str|str list): recipient(s)
        subject (str): message subject
        body (str): message body
        from_ (str): override from address
        html (bool): send as html
    """
    _to = [to_] if isinstance(to_, six.string_types) else to_

    _email = MIMEMultipart('alternative')
    _email['Subject'] = subject
    _email['From'] = from_
    _email['To'] = (", ").join(_to)
    _email["Date"] = formatdate(localtime=True)

    _text = MIMEText(body, 'html' if html else 'plain')
    _email.attach(_text)

    _server = smtplib.SMTP(_PSYOP_EMAIL_SERVER)
    _server.sendmail(from_, _to, _email.as_string())
    _server.quit()

    print 'SENT EMAIL', _to
