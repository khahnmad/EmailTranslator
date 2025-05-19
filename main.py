import imaplib
import email

import quopri
from email import utils
import datetime
from datetime import timezone, timedelta
from email.message import EmailMessage

from transformers import MBartForConditionalGeneration, MBart50TokenizerFast

import re

import smtplib
import csv

import dotenv
import os

import time

# Load env variables
dotenv.load_dotenv()

def import_csv(csv_file:str) -> list[list]:
    # Given a file location, imports the data as a nested list, each row is a new list

    nested_list = []  # initialize list
    with open(csv_file, newline='', encoding='utf-8') as csvfile:  # open csv file
        reader = csv.reader(csvfile, delimiter=',')
        for row in reader:
            nested_list.append(row)
        return nested_list[0]

def export_list(csv_name:str, values):
    # Export a nested list as a csv with a row for each sublist
    with open(csv_name, 'w', newline='', encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(values)

def send_email(body, subject:str):
    msg = EmailMessage()
    msg.set_content(body)

    msg['Subject'] = f"TRANSLATION: {subject}"
    msg['From'] = os.getenv('SENT_EMAIL')
    msg['To'] = os.getenv('READ_EMAIL')

    server = smtplib.SMTP('smtp.gmail.com')
    server.starttls()
    server.login(os.getenv('SENT_USERNAME'),os.getenv('SENT_PASSWORD'))
    server.set_debuglevel(1)
    server.send_message(msg)
    server.close()

def translate_text(text, tokenizer, model):
    encoded_ar = tokenizer(text, return_tensors="pt")
    if len(encoded_ar.encodings[0].tokens)>512:
        num_bins = int(len(encoded_ar.encodings[0].tokens)/512)+1
        bin_size = int(len(text)/num_bins)
        text_chunks = []
        for i in range(num_bins):
            # print(f"{i*bin_size},{(i+1)*bin_size}")
            text_chunks.append(text[i*bin_size:(i+1)*bin_size])
        return " ".join([translate_text(chunk, tokenizer, model) for chunk in text_chunks])
    generated_tokens = model.generate(
        **encoded_ar,
        forced_bos_token_id=tokenizer.lang_code_to_id["en_XX"]
    )
    return tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]

def fetch_emails(search_criteria):
    M = imaplib.IMAP4_SSL(os.getenv('EMAIL_DOMAIN'))
    M.login(os.getenv('READ_USERNAME') , os.getenv('READ_PASSWORD'))
    M.select()
    typ, data = M.search(None, search_criteria)
    return data, M


def reformat_body(text):
    cleaned = []
    for t in text:
        subbed = re.sub(r'(?<!\r\n)\r\n(?!\r\n)', ' ', t)
        cleaned+=subbed.split('\r\n')
    return [x for x in cleaned if x!='' and x!=' ']

def fetch_model_tokenizer():
    model = MBartForConditionalGeneration.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")
    tokenizer = MBart50TokenizerFast.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")
    tokenizer.src_lang='de_DE'
    return model, tokenizer

def translate_emails(search_parameters, time_threshold):
    # Initialize
    try:
        logs = import_csv('email_logs.csv')
    except FileNotFoundError:
        logs = []
    model, tokenizer = fetch_model_tokenizer()
    data, M = fetch_emails(search_criteria=search_parameters)

    # Iterate through fetched data
    count = 0
    for num in data[0].split():
        count += 1
        print(f"\nLooking at email {count}")
        # Check if already translated
        if str(num) in logs:
            print(f" - Already translated")
            continue
        logs.append(num)
        status, data = M.fetch(num, '(RFC822)')
        email_message = email.message_from_bytes(data[0][1])

        # Check if it's older than allowed
        datetime_obj = utils.parsedate_to_datetime(email_message['date'])
        if (datetime.datetime.now(
                tz=timezone.utc) - datetime_obj).days > time_threshold:  # If the message is from more than x days ago
            print(f" - From more than {time_threshold} days ago")
            continue

        print(f" - Fetching body")
        body = []
        for part in email_message.walk():
            if part.get_content_type() == 'text/plain':
                try:
                    p_payload = quopri.decodestring(part.get_payload()).decode('latin-1')
                    if ' ' in p_payload:
                        body.append(p_payload)  # prints the raw text
                    print(f" - Decoded body")
                except ValueError:
                    p_payload = part.get_payload()
                    if ' ' in p_payload:
                        body.append(p_payload)
                    body.append(p_payload)
                    print(f" - Error decoding body")
        if len(body) == 0:
            print(" - No text found - maybe it's a bitmap representation of a picture")
            continue

        body = reformat_body(body)
        a = time.time()
        translated = "\n".join([translate_text(b, model=model, tokenizer=tokenizer) for b in body])
        b = time.time()
        print(f" - Body translation took {(b - a) / 60} minutes")
        subject_translated = translate_text(email_message['subject'], model=model, tokenizer=tokenizer)
        # Resend the email:
        print(f" - Sending email...")
        send_email(body=translated, subject=subject_translated)
        export_list('email_logs.csv', logs)
        print(f"- Sent and logged")

    print(f'PROCESS COMPLETE - CLOSING')
    M.close()
    M.logout()
    return


if __name__ == '__main__':
    # Translate german emails to english and resends them, based on provided search criteria
    time_threshold = 10 # number of days into the past that I'll search
    search_criteria = 'OR (TO "mitarbeiter-list@uni-potsdam.de") (TO "uni-list@uni-potsdam.de")'
    translate_emails(search_criteria, time_threshold)
