# Automated Plant Blog System

An intelligent Django blog system that automatically generates daily posts about plants, flowers, and fruits with detailed content, images, and video URLs.

## Features

- 🌱 **Automated Daily Posts**: Generates posts about plants, flowers, and fruits
- 📸 **Automatic Images**: Fetches relevant images from Unsplash
- 🎥 **Video Integration**: Includes YouTube video links
- 🏷️ **Smart Categorization**: Organizes content by plants, flowers, fruits, gardening, and care
- 📊 **Detailed Plant Info**: Scientific names, care difficulty, watering needs, etc.
- 🔍 **Search & Filter**: Advanced search and category filtering
- 📱 **Responsive Design**: Mobile-friendly templates
- ⚡ **Performance Optimized**: Fast loading with pagination

## Categories

- **Plants**: Houseplants, indoor plants, decorative plants
- **Flowers**: All types of flowering plants and care guides
- **Fruits**: Fruit trees, berry bushes, and harvesting guides
- **Gardening**: General gardening tips and techniques
- **Care**: Plant care, maintenance, and troubleshooting

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the root directory:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI API Keys
GEMINI_API_KEY=your-gemini-api-key-here

# Image API (Optional)
UNSPLASH_ACCESS_KEY=your-unsplash-access-key-here

# YouTube API (Optional)
YOUTUBE_API_KEY=your-youtube-api-key-here
```

### 3. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

### 5. Run the Server

```bash
python manage.py runserver
```

## Usage

### Generate a Single Post

```bash
# Generate today's post (automatic category rotation)
python manage.py generate_post

# Generate post for specific category
python manage.py generate_post --category plants

# Force generation even if post exists
python manage.py generate_post --force
```

### Automated Daily Posts

```bash
# Generate daily post
python manage.py auto_post_daily

# Dry run (see what would be generated)
python manage.py auto_post_daily --dry-run
```

### Schedule Daily Posts

Add to your crontab for automatic daily posting:

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * cd /path/to/your/project && python manage.py auto_post_daily
```

## API Keys Setup

### 1. Gemini AI (Required)
- Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
- Create an API key
- Add to `.env` as `GEMINI_API_KEY`

### 2. Unsplash (Optional - for images)
- Go to [Unsplash Developers](https://unsplash.com/developers)
- Create an application
- Get your access key
- Add to `.env` as `UNSPLASH_ACCESS_KEY`

### 3. YouTube API (Optional - for better video search)
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Enable YouTube Data API v3
- Create credentials
- Add to `.env` as `YOUTUBE_API_KEY`

## Daily Topic Rotation

The system automatically rotates through topics:

- **Day 1-5**: Plants (Monstera, Snake Plant, Pothos, etc.)
- **Day 6-10**: Flowers (Rose, Orchid, Tulip, etc.)
- **Day 11-15**: Fruits (Strawberry, Tomato, Citrus, etc.)
- **Day 16-20**: Gardening (Organic tips, Container gardening, etc.)
- **Day 21-25**: Care (Watering, Light requirements, etc.)
- **Day 26-31**: Cycles back to plants

## Admin Interface

Access the admin panel at `/admin/` to:

- Manage posts, categories, and tags
- Edit generated content
- Control publishing status
- View analytics and view counts
- Bulk actions for multiple posts

## Templates

The system includes responsive templates:

- **Homepage**: Featured posts and latest content
- **Blog**: All posts with filtering
- **Post Detail**: Full article with related posts
- **Category Pages**: Posts filtered by category
- **Search Results**: Search functionality
- **Gallery**: Visual post showcase

## Customization

### Adding New Topics

Edit `blog/management/commands/generate_post.py` and add topics to the `get_daily_topics()` method.

### Custom Categories

Add new categories in the `Post` model's `CATEGORY_CHOICES`.

### Template Styling

Modify templates in the `templates/blog/` directory to match your design.

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all API keys are correctly set in `.env`
2. **Image Loading**: Check Unsplash API key and rate limits
3. **Content Generation**: Verify Gemini API key and quota
4. **Database Errors**: Run migrations if models have changed

### Logs

Check Django logs for detailed error information:

```bash
python manage.py runserver --verbosity=2
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on GitHub. 