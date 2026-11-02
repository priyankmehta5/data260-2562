"""Run the HW8 Planner as a separate Kafka consumer process."""

from backend.hw08_agents import main

if __name__ == "__main__":
    main("planner")
