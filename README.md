# Haven: A Privacy-First Safe Space AI

**Haven** is a Python-based mental health companion designed to act as a supportive listening ear. It prioritizes user privacy by offering an ephemeral "safe space" for venting without data permanence, while also providing optional tools for mood tracking and professional resource connection.

## 📖 Project Overview

Haven was built on the belief that everyone deserves a non-judgmental space to talk. It operates in two distinct modes:
1.  **Safe Space Mode:** A private, real-time conversation loop where your thoughts are heard but **never recorded**.
2.  **Check-In Mode:** An optional tracking feature that allows you to log interactions, monitor sentiment trends, and schedule appointments if you choose to do so.

## ✨ Key Features

* **Ephemeral "Safe Space" Loop:** A dedicated mode that allows you to converse with the AI without any data being saved to the database. It is designed purely for the moment.
* **Sentiment Analysis:** Powered by **TextBlob**, Haven analyzes your input to detect emotional polarity (positive/negative) and responds with appropriate empathy.
* **Entity Extraction:** Uses **spaCy** to identify key subjects and context within your sentences.
* **Resource Hub:** Provides immediate access to vetted mental health resources (CDC, NIMH, etc.) for topics like anxiety, trauma, and depression.
* **Appointment Scheduling:** A built-in system to book and log appointments with counselors securely.
* **Secure Logging (Optional):** Uses **Flask-SQLAlchemy** to manage persistent data only when you use the "Check-in" or "Appointment" features.

## 🛠️ Tech Stack

* **Language:** Python 3.x
* **Frameworks:** Flask, Flask-SQLAlchemy
* **NLP Engines:** TextBlob, spaCy (`en_core_web_sm`)
* **Database:** MySQL (via PyMySQL)
* **Interface:** Command Line Interface (CLI)
