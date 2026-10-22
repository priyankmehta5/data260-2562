# MongoDB and File-Based Memory Comparison

MongoDB-backed memory is more inspectable through collection queries and scales naturally across many users and sessions. It persists after an application restart when MongoDB is available, and its separate messages, summaries, and episodes collections support indexed retrieval. It is the better choice for conversational history and episodic facts that must be shared across sessions.

File-based memory is easier to inspect in Git, works without a database service, and is convenient for durable project instructions or a small number of stable facts. It is less suitable for high-volume sessions because one file becomes a contention and scaling point. It is useful for facts that must not be forgotten, such as safety constraints and project conventions, because changes are visible in code review.

The two systems complement one another: MongoDB stores user/session conversation state, while AGENT.md and MEMORY.md store durable project-level instructions and consolidated facts.
