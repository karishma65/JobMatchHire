"""
Predefined Skill Dictionary and Aliases for Resume Parsing
Covers modern software engineering, data science, DevOps, cloud, mobile, and soft skills.
"""

SKILLS_DICTIONARY = [
    # Programming Languages
    "Python", "Java", "C++", "C", "C#", "JavaScript", "TypeScript", "Go", "Golang", 
    "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "Dart", "MATLAB", 
    "Bash", "Shell", "PowerShell", "Perl", "SQL",

    # Web & Full Stack Frameworks
    "FastAPI", "Flask", "Django", "React", "React.js", "Angular", "Vue", "Vue.js",
    "Next.js", "Node.js", "Express", "Express.js", "Spring Boot", "ASP.NET", ".NET",
    "HTML", "HTML5", "CSS", "CSS3", "TailwindCSS", "Bootstrap", "jQuery", "GraphQL",
    "REST API", "RESTful API", "Microservices", "WebSockets", "gRPC",

    # Databases & Storage
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Cassandra", "DynamoDB",
    "Elasticsearch", "Oracle", "Neo4j", "Firebase", "Supabase", "Snowflake", "BigQuery",

    # Cloud & DevOps
    "AWS", "Amazon Web Services", "Azure", "Google Cloud", "GCP", "Docker", "Kubernetes",
    "Terraform", "Ansible", "Jenkins", "CI/CD", "GitLab CI", "GitHub Actions",
    "Linux", "Unix", "Nginx", "Apache", "Prometheus", "Grafana", "Kafka", "RabbitMQ",

    # Data Science, AI & Machine Learning
    "Machine Learning", "Deep Learning", "Artificial Intelligence", "NLP", "Natural Language Processing",
    "Computer Vision", "PyTorch", "TensorFlow", "Keras", "Scikit-Learn", "Pandas",
    "NumPy", "SciPy", "OpenCV", "HuggingFace", "Transformers", "LLMs", "LangChain",
    "Data Analysis", "Data Visualization", "Data Mining", "Tableau", "Power BI",

    # Software Engineering & Architecture
    "Git", "GitHub", "GitLab", "Bitbucket", "Agile", "Scrum", "JIRA",
    "Object-Oriented Programming", "OOP", "Data Structures", "Algorithms",
    "System Design", "Distributed Systems", "Design Patterns", "Unit Testing",
    "Test-Driven Development", "TDD", "Integration Testing", "PyTest", "Jest",

    # Soft & Professional Skills
    "Communication", "Leadership", "Problem Solving", "Teamwork", "Project Management",
    "Time Management", "Critical Thinking", "Collaboration"
]

# Standard canonical mapping for synonyms and common variations
SKILL_ALIASES = {
    # Python variants
    "advanced python": "Python",
    "core python": "Python",
    "python 3": "Python",
    "python3": "Python",
    "python programming": "Python",
    "programming in python": "Python",

    # NLP variants
    "natural language processing": "NLP",
    "nlp": "NLP",

    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo": "MongoDB",
    "sqlite3": "SQLite",

    # Frontend & Fullstack
    "react.js": "React",
    "reactjs": "React",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express.js": "Express",
    "expressjs": "Express",
    "tailwind": "TailwindCSS",
    "tailwind css": "TailwindCSS",

    # Cloud & DevOps
    "amazon web services": "AWS",
    "aws": "AWS",
    "google cloud platform": "GCP",
    "google cloud": "GCP",
    "k8s": "Kubernetes",
    "ci / cd": "CI/CD",
    "cicd": "CI/CD",

    # Data Science & Machine Learning
    "scikit learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",

    # Languages & APIs
    "golang": "Go",
    "restful api": "REST API",
    "restful": "REST API",
    "rest apis": "REST API"
}

