# 🚢 PortPulse AI

PortPulse AI is a real-time logistics visibility platform that simulates container movement events, streams them through Kafka, stores them in PostgreSQL, visualizes operational insights in Streamlit, and enables natural-language analytics using Gemini.

## Architecture

Container Events Simulator
        ↓
Apache Kafka
        ↓
Kafka Consumer
        ↓
PostgreSQL
        ↓
Streamlit Dashboard
        ↓
Gemini AI Agent

## Features

- Real-time container movement simulation
- Kafka event streaming architecture
- PostgreSQL operational data store
- Interactive Streamlit dashboard
- Container delay monitoring
- Port performance visibility
- Gemini-powered natural language analytics
- Read-only SQL generation and execution

## Tech Stack

### Data Engineering
- Apache Kafka
- PostgreSQL
- Docker

### Analytics
- Python
- Pandas
- Streamlit

### AI
- Gemini 3.5 Flash
- Natural Language to SQL

## Example Questions

- Which containers are currently delayed?
- Which ports have the highest average delay?
- Which carrier has the highest delay exposure?
- Show the latest status of 10 containers.
- Which containers require immediate attention?

## Project Structure

```text
.
├── producer.py
├── consumer.py
├── dashboard.py
├── docker-compose.yml
├── agent/
├── pages/
├── airflow/
└── requirements.txt
```

## Future Enhancements

- Predictive delay forecasting
- Carrier performance scoring
- Automated logistics recommendations
- Multi-modal shipment intelligence
- Slack / Teams integration

## Author

Yujata Pasricha
