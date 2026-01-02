# Reddit Watch

A Django application for tracking Reddit campaigns.

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
