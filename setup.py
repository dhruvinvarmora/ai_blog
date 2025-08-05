#!/usr/bin/env python3
"""
Setup script for Automated Plant Blog System
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        print(f"Error output: {e.stderr}")
        return False

def create_env_file():
    """Create .env file with template"""
    env_content = """# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI API Keys
GEMINI_API_KEY=your-gemini-api-key-here

# Image API (Optional)
UNSPLASH_ACCESS_KEY=your-unsplash-access-key-here

# YouTube API (Optional)
YOUTUBE_API_KEY=your-youtube-api-key-here
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file with template")
        print("⚠️  Please edit .env file with your actual API keys")
    else:
        print("ℹ️  .env file already exists")

def main():
    print("🌱 Setting up Automated Plant Blog System")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Create .env file
    create_env_file()
    
    # Run migrations
    if not run_command("python manage.py makemigrations", "Creating database migrations"):
        print("❌ Failed to create migrations")
        sys.exit(1)
    
    if not run_command("python manage.py migrate", "Applying database migrations"):
        print("❌ Failed to apply migrations")
        sys.exit(1)
    
    # Create superuser if needed
    print("\n👤 Do you want to create a superuser? (y/n): ", end="")
    create_superuser = input().lower().strip()
    
    if create_superuser in ['y', 'yes']:
        run_command("python manage.py createsuperuser", "Creating superuser")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python manage.py runserver")
    print("3. Visit http://localhost:8000")
    print("4. Generate your first post: python manage.py generate_post")
    print("\n📚 For more information, see README.md")

if __name__ == "__main__":
    main() 