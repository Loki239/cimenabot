#!/usr/bin/env python3
"""
Script to create a .env file with API tokens
Run this script once to generate your .env file
"""
import os

def main():
    # Check if .env file already exists
    if os.path.exists('.env'):
        print("⚠️  .env file already exists. To recreate it, delete it first.")
        return
    
    # Get tokens from user
    print("📝 Enter your API tokens:")
    telegram_token = input("Telegram Bot Token: ")
    kinopoisk_token = input("Kinopoisk API Token: ")
    
    # Create .env file
    with open('.env', 'w') as f:
        f.write(f"TELEGRAM_TOKEN={telegram_token}\n")
        f.write(f"KINOPOISK_TOKEN={kinopoisk_token}\n")
    
    print("✅ .env file created successfully!")
    print("🔒 Your tokens are now securely stored in the .env file.")
    print("⚠️  Do not commit the .env file to version control!")

if __name__ == "__main__":
    main() 