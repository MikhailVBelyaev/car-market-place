Best Practices

	1.	Use a Migration Tool: Tool Flyway are industry standards and make updates safer and more predictable.
	2.	Git as Source of Truth: Store all database scripts (init and updates) in Git to keep a version history.
	3.	Test Updates: Use a staging environment to test scripts before running them in production.
	4.	Automate CI/CD Pipelines: Automate the delivery process using CI/CD pipelines to reduce manual errors. (GitHub Actions)
	5. Use Jenkins for CI/CD. Run all components (including Jenkins) in Docker containers for consistency and isolation.