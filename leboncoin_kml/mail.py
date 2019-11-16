import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from leboncoin_kml.config import Config


class Sender(object):
    def __init__(self, config=Config()):
        self.config = config
        # creates SMTP session
        s = smtplib.SMTP('smtp.gmail.com', 587)

        # start TLS for security
        s.starttls()

        # Authentication
        s.login(config.email_sender, config.email_password)
        self.s = s

    def __call__(self, attachments, subject="Nouvelles annonces LBC", body=None):
        if body is None:
            body = "En pièce jointe, veuillez trouver les nouvelles annonces correspondant à vos critères"

        conf = self.config
        fromaddr = conf.email_sender
        toaddr = conf.email_receivers

        # instance of MIMEMultipart
        msg = MIMEMultipart()

        # storing the senders email address
        msg['From'] = fromaddr

        # storing the receivers email address
        msg['To'] = toaddr

        # storing the subject
        msg['Subject'] = subject

        # attach the body with the msg instance
        msg.attach(MIMEText(body, 'plain'))

        # open the file to be sent
        for filename, attachment in attachments.items():
            # instance of MIMEBase and named as p
            p = MIMEBase('application', 'octet-stream')

            # To change the payload into encoded form
            p.set_payload(attachment)

            # encode into base64
            encoders.encode_base64(p)

            p.add_header('Content-Disposition', "attachment; filename= %s" % filename)

            # attach the instance 'p' to instance 'msg'
            msg.attach(p)

        # Converts the Multipart msg into a string
        text = msg.as_string()

        # sending the mail
        s = self.s
        s.sendmail(fromaddr, toaddr.split(', '), text)

        # terminating the session
        s.quit()


if __name__ == '__main__':
    s = Sender()
    s(dict(test=b'abcdef'))
