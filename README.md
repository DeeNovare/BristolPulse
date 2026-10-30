# BristolPulse Event Management System

A university coursework web application built with **Python, Flask, MySQL, HTML, CSS and Bootstrap**. This repository is intended for private portfolio review unless publication permission is confirmed.

## Features
- Account registration and login
- Event browsing, search and filtering
- Ticket booking and booking receipts
- Student discount calculations (10%)
- Booking cancellation with simulated refund/penalty logic
- Admin event management, availability toggles and booking reports

Payments are simulated. Some homepage featured events are static UI content.

## Local setup
1. Install Python 3 and MySQL Server.
2. Create a Python virtual environment (recommended), then run `pip install -r requirements.txt`.
3. Import `bristol_pulse_v2_schema.sql` into MySQL. **This file creates tables only; it does not include demo accounts or events.** If you have a separate local data export, restore it privately; do not upload real user data.
4. Copy `.env.example` to `.env` and edit the values for your local MySQL installation. Keep `.env` private.
5. Run `python app.py`, then open `http://127.0.0.1:5000/`.

The application expects appropriate event and category records in the database to display event listings. Register a local user through the site to test user features. Admin functions require an account with the appropriate `user_type` in your local database.

## Notes
- Do not use this coursework application as a production service without additional security review and testing.
- The original coursework instructions, historical database exports, generated Python caches and hardcoded configuration secrets are excluded from this portfolio package.
- Public release should be checked against applicable coursework and university rules.
