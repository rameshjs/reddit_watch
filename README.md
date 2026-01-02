### I built Reddit Watch for my own use because I wanted a better way to monitor specific keywords on Reddit without constantly checking the site. My main goal is to use AI to filter posts by context—separating the signal from the noise—rather than just getting a raw list of every keyword match.

## How it works

- **Campaigns**: I create campaigns for different topics I want to track.
- **Background Monitoring**: It runs periodic checks using **Celery** and **Redis** so I don't have to do it manually.
- **Storage**: Everything gets saved to a **Postgres** database for analysis.
- **Development Status**: Currently, it's set up with a simulation engine (`check_reddit_campaign`) that generates mock data. This lets me test the UI and scheduling logic without worrying about Reddit API limits while building out the core features.

## Tech Stack

- **Backend**: Django, Python
- **Task Queue**: Celery, Redis
- **Database**: PostgreSQL
- **Infrastructure**: Docker, Docker Compose

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd reddit_watch
   ```

2. **Create environment variables:**
   Copy the example environment file:
   ```bash
   cp .env.example .env.dev
   ```
   *Note: Update `.env.dev` with your configuration if needed.*

3. **Build and run with Docker:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   Open [http://localhost:8000](http://localhost:8000) in your browser.

## Development

- **Run migrations:**
  ```bash
  docker-compose exec web python manage.py migrate
  ```

- **Create superuser:**
  ```bash
  docker-compose exec web python manage.py createsuperuser
  ```
