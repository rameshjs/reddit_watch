### I built Reddit Watch for my own use because I wanted a better way to monitor specific keywords on Reddit without constantly checking the site. My main goal is to use AI to filter posts by context to separate the signal from the noise, rather than just getting a raw list of every keyword match.

## How it works

I create campaigns for different topics I want to track, and the application handles the rest in the background using **Celery** and **Redis** for periodic checks. This automation saves me from manual monitoring. All data is stored in a **Postgres** database for future analysis.

Currently, the project is in a development phase where it uses a simulation engine (`check_reddit_campaign`) to generate mock data. This setup allows me to test the scheduling logic and UI components without hitting Reddit API limits while I finalize the core monitoring features.

## Tech Stack

The backend is built with **Django** and **Python**, relying on **Celery** and **Redis** for background tasks and **PostgreSQL** for data storage. The entire infrastructure is containerized using **Docker** and **Docker Compose** for consistent deployment.

## Prerequisites

To run this locally, you'll need [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine.

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
   *Note: Update `.env.dev` with your custom configuration if needed.*

3. **Build and run:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   Open [http://localhost:8000](http://localhost:8000) in your browser.

## Development

**Run migrations:**
```bash
docker-compose exec web python manage.py migrate
```

**Create superuser:**
```bash
docker-compose exec web python manage.py createsuperuser
```
