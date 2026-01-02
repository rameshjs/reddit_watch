### Reddit Watch

I built Reddit Watch for my own use because I wanted a better way to monitor specific keywords on Reddit without constantly checking the site. My main goal is to use AI to filter posts by context to separate the signal from the noise, rather than just getting a raw list of every keyword match.

## How it works

The application operates in two distinct stages to ensure meaningful data matching:

1.  **Global Ingestion**: A background task continuously fetches new posts and comments from `r/all` using the Reddit JSON API. This ensures we have a local cache of recent Reddit activity. To respect Reddit's API limits, this uses cursor-based pagination and intelligent back-off (resetting only when the feed id becomes stale).
2.  **Campaign Matching**: Separate background tasks run for each compaign (at user-defined intervals) to scan the locally ingested data against your specific keywords. This decoupling allows for heavy processing or future AI analysis without slowing down the ingestion pipeline.

All data is stored in a **Postgres** database, and tasks are orchestrated by **Celery** with **Redis** as the broker.

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
