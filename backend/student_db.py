import sqlite3, os, hashlib, secrets, base64, re
from collections import defaultdict
from datetime import datetime, timedelta

DB_PATH = os.getenv("DB_PATH", "/app/data/Faculty_database.db")


def get_conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def setup_student_db():
    with get_conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                university TEXT DEFAULT 'SUST',
                department TEXT DEFAULT '',
                year TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS phd_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT DEFAULT '',
                university TEXT DEFAULT 'SUST',
                department TEXT DEFAULT '',
                supervisor TEXT DEFAULT '',
                research_area TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                year_enrolled TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS phd_student_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phd_student_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (phd_student_id) REFERENCES phd_students(id)
            );

            CREATE TABLE IF NOT EXISTS student_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS student_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                post_type TEXT DEFAULT 'work',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS student_saved_faculty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                faculty_id INTEGER NOT NULL,
                added_at TEXT DEFAULT (datetime('now')),
                UNIQUE(student_id, faculty_id),
                FOREIGN KEY (student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS student_saved_phd (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                phd_student_id INTEGER NOT NULL,
                added_at TEXT DEFAULT (datetime('now')),
                UNIQUE(student_id, phd_student_id),
                FOREIGN KEY (student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS student_saved_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                target_student_id INTEGER NOT NULL,
                added_at TEXT DEFAULT (datetime('now')),
                UNIQUE(student_id, target_student_id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (target_student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                student_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS student_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                label TEXT DEFAULT '',
                mime TEXT DEFAULT 'application/octet-stream',
                data BLOB,
                uploaded_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
        """)
        _ensure_student_columns(con)
        con.commit()
    _seed_phd_students()
    _seed_demo_students()


def _ensure_student_columns(con):
    """Migrate older DBs: add newer columns if missing."""
    cols = [r[1] for r in con.execute("PRAGMA table_info('students')").fetchall()]
    extra = {
        "research_interests": "TEXT DEFAULT ''",
        "research_summary":   "TEXT DEFAULT ''",
        "cv_filename":        "TEXT DEFAULT ''",
        "cv_data":            "BLOB",
        "photo_data":         "BLOB",
        "photo_mime":         "TEXT DEFAULT ''",
    }
    for col, decl in extra.items():
        if col not in cols:
            con.execute(f"ALTER TABLE students ADD COLUMN {col} {decl}")
            print(f"  + students.{col} column added")

    post_cols = [r[1] for r in con.execute("PRAGMA table_info('student_posts')").fetchall()]
    for col, decl in {"image_data": "BLOB", "image_mime": "TEXT DEFAULT ''"}.items():
        if col not in post_cols:
            con.execute(f"ALTER TABLE student_posts ADD COLUMN {col} {decl}")
            print(f"  + student_posts.{col} column added")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


# Must match the number of rows in phd_data below — if the DB already has
# this many, seeding is skipped (a reseed wipes embeddings, forcing a slow
# re-embed on every startup).
_TARGET_PHD_COUNT = 33

def _seed_phd_students():
    with get_conn() as con:
        existing = con.execute("SELECT COUNT(*) FROM phd_students").fetchone()[0]
        if existing >= _TARGET_PHD_COUNT:
            print(f"  PhD students already seeded ({existing} rows) — skipping.")
            return
        # Clear and re-seed so IDs are consistent
        con.execute("DELETE FROM phd_student_tags")
        con.execute("DELETE FROM phd_students")
        con.commit()

    phd_data = [
        # ── CSE ──────────────────────────────────────────────────────────────
        ("Rafiul Islam", "rafiul@sust.edu", "SUST", "CSE",
         "Dr. Enamul Hassan",
         "Natural Language Processing, Bangla Text Summarization, Transformer Models, Low-resource NLP",
         "PhD student working on low-resource Bangla NLP. Thesis focuses on abstractive summarization using fine-tuned transformer models. Exploring cross-lingual transfer learning and multilingual BERT variants.",
         "2022"),
        ("Tasneem Binte Amin", "tasneem@sust.edu", "SUST", "CSE",
         "Marium-E-Jannat",
         "Machine Learning, Human-Computer Interaction, Accessibility Technology, User Modeling",
         "Researching ML-based accessibility tools for visually impaired users in low-literacy contexts. Work combines probabilistic user models with adaptive interface design.",
         "2021"),
        ("Md. Sabbir Hossain", "sabbir@sust.edu", "SUST", "CSE",
         "Mahruba Sharmin Chowdhury",
         "Deep Learning, Computer Vision, Medical Image Analysis, Retinal Disease Detection",
         "Working on automated detection of retinal diseases from fundus images using CNNs. Collaborating with SUST medical faculty for annotated dataset collection and clinical validation.",
         "2023"),
        ("Shirin Akter", "shirin@sust.edu", "SUST", "CSE",
         "Summit Haque",
         "Cybersecurity, Network Intrusion Detection, Graph Neural Networks, Anomaly Detection",
         "Building ML-based intrusion detection systems for enterprise networks. Applies graph neural networks to model network traffic anomalies and zero-day attack patterns.",
         "2023"),
        ("Mahbuba Khanam", "mahbuba@sust.edu", "SUST", "CSE",
         "Ayesha Tasnim",
         "Bioinformatics, Genomics, Protein Structure Prediction, Drug Discovery",
         "Using deep learning to predict protein-protein interaction sites. Collaborating with the biology department for wet-lab validation of computational predictions.",
         "2021"),
        ("Rezaul Karim", "rezaul@sust.edu", "SUST", "CSE",
         "MOQSADUR RAHMAN",
         "Computer Vision, Object Detection, Edge AI, Embedded Systems, Agricultural Drones",
         "Developing lightweight object detection models for low-power embedded systems. Target deployment on edge devices for precision agriculture and drone-based crop monitoring.",
         "2023"),
        ("Imtiaz Hossain", "imtiaz@sust.edu", "SUST", "CSE",
         "Abdullah Al Thaki",
         "Graph Neural Networks, Knowledge Graphs, Relational Learning, Drug Interaction Prediction",
         "Researching graph contrastive learning for biomedical knowledge graphs. Work focuses on predicting unknown drug-drug interactions by modeling molecular relationships in heterogeneous graphs.",
         "2022"),
        ("Sabrina Parvin", "sabrina@sust.edu", "SUST", "CSE",
         "Md. Shymon Islam",
         "Federated Learning, Privacy-Preserving Machine Learning, Healthcare AI",
         "Building federated learning frameworks for healthcare applications where patient data cannot leave local hospitals. Focuses on communication-efficient aggregation and differential privacy guarantees.",
         "2023"),
        ("Minhaz Uddin", "minhaz@sust.edu", "SUST", "CSE",
         "Mahruba Sharmin Chowdhury",
         "Speech Recognition, Bangla ASR, Acoustic Modeling, End-to-End Deep Learning",
         "Developing a large-vocabulary automatic speech recognition system for Bangla dialects. Working on data augmentation strategies for low-resource dialect adaptation.",
         "2021"),
        ("Anika Sultana", "anika@sust.edu", "SUST", "CSE",
         "Summit Haque",
         "Sentiment Analysis, Opinion Mining, Social Media NLP, Bangla Hate Speech Detection",
         "Researching fine-grained sentiment analysis on Bengali social media text. Building a benchmark dataset for Bangla hate speech and toxicity classification.",
         "2022"),
        ("Saad Al-Farabi", "saad@sust.edu", "SUST", "CSE",
         "Enamul Hassan",
         "Large Language Models, Retrieval-Augmented Generation, Question Answering, Knowledge Grounding",
         "Studying hallucination mitigation in large language models through retrieval-augmented generation. Benchmarking RAG pipelines on low-resource Bangla knowledge bases.",
         "2023"),
        ("Nadia Rahman", "nadia@sust.edu", "SUST", "CSE",
         "MOQSADUR RAHMAN",
         "Reinforcement Learning, Robotics, Autonomous Navigation, Multi-Agent Systems",
         "Applying deep reinforcement learning to autonomous robot navigation in dynamic indoor environments. Research includes multi-agent coordination for warehouse logistics.",
         "2022"),
        # ── EEE ──────────────────────────────────────────────────────────────
        ("Arif Mahmud", "arif@sust.edu", "SUST", "EEE",
         "Dr. Ahmad Hasan Nury",
         "IoT, Smart Grid, Energy Systems, Renewable Energy, Demand Forecasting",
         "Developing IoT-based smart metering systems for rural electrification in Bangladesh. Interested in solar energy optimization and ML-based demand forecasting.",
         "2021"),
        ("Nur-E-Alam Siddique", "nalam@sust.edu", "SUST", "EEE",
         "Dr. Ahmad Hasan Nury",
         "Power Systems, Fault Detection, SCADA, Machine Learning for Grid Stability",
         "Applying ML to detect and classify power grid faults in real-time using SCADA telemetry data. Work targets the Bangladesh national grid's transmission infrastructure.",
         "2022"),
        ("Faria Tasnim", "faria@sust.edu", "SUST", "EEE",
         "Md Sifat Tanveer",
         "Signal Processing, Brain-Computer Interface, EEG Classification, Deep Learning",
         "Developing deep learning models for motor imagery EEG classification in brain-computer interfaces. Investigating transfer learning between subjects to reduce calibration overhead.",
         "2023"),
        ("Arman Hossain", "arman@sust.edu", "SUST", "EEE",
         "Md Sifat Tanveer",
         "Wireless Communications, 5G/6G, Channel Estimation, MIMO, Deep Learning for PHY",
         "Applying deep neural networks to channel estimation and beamforming in massive MIMO systems. Research includes over-the-air computation for federated learning over 5G.",
         "2021"),
        # ── STA ──────────────────────────────────────────────────────────────
        ("Noushin Afrin", "noushin@sust.edu", "SUST", "STA",
         "Dr. Md. Azizul Baten",
         "Statistical Machine Learning, Time Series Forecasting, Climate Data Analysis, Flood Prediction",
         "Using ML and statistical models to forecast flood events in Bangladesh using BWDB hydrological data. Interdisciplinary research combining statistics and environmental science.",
         "2022"),
        ("Fahmida Sultana", "fahmida@sust.edu", "SUST", "STA",
         "Dr. Mohammad Ohid Ullah",
         "Public Health Informatics, Survival Analysis, Cancer Epidemiology, Biostatistics",
         "Applying survival analysis and ML to study cancer outcomes in Bangladeshi patients. Dataset involves 5000+ patients from Sylhet hospitals.",
         "2022"),
        ("Kamrul Hasan", "kamrul@sust.edu", "SUST", "STA",
         "Dr. Md. Azizul Baten",
         "Bayesian Statistics, Causal Inference, Epidemiology, Missing Data Imputation",
         "Developing Bayesian causal inference methods for observational health data with high missingness. Working on applications in tuberculosis treatment outcome modelling in Bangladesh.",
         "2023"),
        # ── IPE ──────────────────────────────────────────────────────────────
        ("Tanvir Ahmed Bhuiyan", "tanvir@sust.edu", "SUST", "IPE",
         "Dr. Mohammad Muhshin Aziz Khan",
         "Manufacturing AI, Predictive Maintenance, Industry 4.0, Deep Learning for Sensors",
         "Applying deep learning to predictive maintenance in textile manufacturing. Collecting vibration and temperature sensor data from local garment factories.",
         "2022"),
        ("Md. Mehedi Kibria Jr.", "mkibria@sust.edu", "SUST", "IPE",
         "Md. Mehedi Hasan Kibria",
         "Supply Chain Optimization, Operations Research, Machine Learning, Logistics",
         "Using ML and combinatorial optimization to redesign resilient supply chains for Bangladesh's RMG sector. Models disruption risk using historical shipment and customs data.",
         "2023"),
        ("Sadia Islam Mim", "sadia@sust.edu", "SUST", "IPE",
         "Md. Jahedul Alam",
         "Additive Manufacturing, 3D Printing Parameter Optimization, Fused Deposition Modeling",
         "Optimizing FDM printing parameters using Bayesian optimization and ML regression models. Focuses on mechanical strength and surface quality of printed polymer parts.",
         "2022"),
        # ── CEE ──────────────────────────────────────────────────────────────
        ("Hasibul Haque", "hasibul@sust.edu", "SUST", "CEE",
         "Dr. Ahmad Hasan Nury",
         "Hydrology, Remote Sensing, Climate Change, GIS, Machine Learning for Water Resources",
         "Using satellite remote sensing and ML to model surface water dynamics in the haor wetlands of Sylhet. Focuses on predicting seasonal inundation under climate change scenarios.",
         "2021"),
        ("Tania Begum", "tania@sust.edu", "SUST", "CEE",
         "Dr. Ahmad Hasan Nury",
         "Air Quality Modeling, Atmospheric Science, Deep Learning, Pollution Forecasting",
         "Developing deep learning models to forecast PM2.5 concentration in Dhaka and Sylhet using meteorological and traffic data. Work contributes to Bangladesh's air quality early-warning system.",
         "2023"),
        # ── PHY ──────────────────────────────────────────────────────────────
        ("Raihan Kabir", "raihan@sust.edu", "SUST", "PHY",
         "Prof. Md. Hasan",
         "Computational Physics, Density Functional Theory, Materials Science, Solar Cell Efficiency",
         "Using DFT simulations to discover new perovskite materials for high-efficiency solar cells. Collaborating with CSE department to accelerate screening with ML surrogate models.",
         "2022"),
        ("Sumaya Khanam", "sumaya@sust.edu", "SUST", "PHY",
         "Prof. Md. Hasan",
         "Quantum Computing, Quantum Error Correction, Variational Quantum Algorithms",
         "Studying noise characterization and error mitigation in near-term quantum circuits. Collaborating with IBM Quantum to benchmark variational quantum eigensolver performance.",
         "2023"),
        # ── CHE ──────────────────────────────────────────────────────────────
        ("Aminul Islam Chowdhury", "aminul@sust.edu", "SUST", "CHE",
         "Prof. Kamrul Ahsan",
         "Computational Chemistry, Molecular Dynamics, Drug Discovery, Cheminformatics",
         "Using molecular dynamics simulations and graph neural networks to predict binding affinity of small molecules to disease targets. Focus on antibiotic-resistant bacterial proteins.",
         "2022"),
        # ── GEB / BAN ─────────────────────────────────────────────────────────
        ("Protik Das", "protik@sust.edu", "SUST", "GEB",
         "Dr. Md. Azizul Baten",
         "Financial Econometrics, Stock Market Prediction, Machine Learning, Time Series",
         "Applying LSTM and transformer models to predict Dhaka Stock Exchange price movements. Incorporating macroeconomic indicators and sentiment data from financial news.",
         "2023"),
        ("Lamia Sharmin", "lamia@sust.edu", "SUST", "BAN",
         "Azmery Sultana",
         "Business Analytics, Customer Churn Prediction, Deep Learning, CRM",
         "Using deep learning for customer churn prediction in Bangladesh's telecom sector. Integrating call detail records, service complaint logs, and social data.",
         "2022"),
        # ── FET ──────────────────────────────────────────────────────────────
        ("Towhid Hossain", "towhid@sust.edu", "SUST", "FET",
         "Md. Amjad Patwary",
         "Food Quality Detection, Computer Vision, Deep Learning, Hyperspectral Imaging",
         "Developing a CNN-based system to detect adulteration and freshness in food products using hyperspectral imaging. Targeting deployment in Bangladeshi food processing factories.",
         "2021"),
        # ── MAT ──────────────────────────────────────────────────────────────
        ("Sohel Rana", "sohel@sust.edu", "SUST", "MAT",
         "Prof. Abdur Rahman",
         "Applied Mathematics, Numerical Methods, Partial Differential Equations, Scientific Computing",
         "Developing high-order numerical schemes for solving nonlinear PDEs arising in fluid dynamics and heat transfer. Applies ML-based solvers (physics-informed neural networks) as hybrid alternatives.",
         "2022"),
        ("Mariam Akter", "mariam@sust.edu", "SUST", "MAT",
         "Prof. Abdur Rahman",
         "Operations Research, Integer Programming, Scheduling Optimization, Heuristic Algorithms",
         "Working on nurse scheduling and resource allocation in hospitals using integer programming and metaheuristics. Partnering with a Sylhet hospital for real-world deployment.",
         "2023"),
        # ── PME ──────────────────────────────────────────────────────────────
        ("Faisal Ahmed", "faisal@sust.edu", "SUST", "PME",
         "Md. Numan Hossain",
         "Petroleum Engineering, Gas Production Forecasting, Machine Learning, Reservoir Simulation",
         "Applying ML models to predict gas production trajectories from well-log data in Bangladeshi gas fields. Uses decline curve analysis combined with gradient boosting.",
         "2021"),
    ]

    tag_map = {
        "Rafiul Islam":           ["Looking for research partner in NLP", "Open to collaboration", "Seeking co-author"],
        "Tasneem Binte Amin":     ["Open to collaboration in HCI", "Looking for partner in ML", "Seeking co-author"],
        "Md. Sabbir Hossain":     ["Looking for medical data partner", "Open to cross-departmental collaboration"],
        "Shirin Akter":           ["Looking for cybersecurity research partner", "Open to collaboration"],
        "Mahbuba Khanam":         ["Looking for biology co-author", "Open to bioinformatics collaboration"],
        "Rezaul Karim":           ["Looking for partner in computer vision", "Seeking embedded systems collaborator"],
        "Imtiaz Hossain":         ["Looking for partner in graph ML", "Open to biomedical AI collaboration"],
        "Sabrina Parvin":         ["Looking for partner in federated learning", "Seeking co-author in healthcare AI"],
        "Minhaz Uddin":           ["Looking for speech/audio data partner", "Open to collaboration in Bangla NLP"],
        "Anika Sultana":          ["Looking for NLP co-author", "Seeking Bangla dataset collaboration"],
        "Saad Al-Farabi":         ["Looking for partner in LLM research", "Open to RAG collaboration"],
        "Nadia Rahman":           ["Looking for partner in RL / robotics", "Open to industry collaboration"],
        "Arif Mahmud":            ["Open to IoT collaboration", "Looking for industry partner"],
        "Nur-E-Alam Siddique":    ["Looking for partner in power systems AI", "Open to industry data collaboration"],
        "Faria Tasnim":           ["Looking for BCI research partner", "Seeking co-author in signal processing"],
        "Arman Hossain":          ["Looking for partner in wireless ML", "Open to 5G/6G research collaboration"],
        "Noushin Afrin":          ["Looking for partner in climate ML", "Seeking co-author for journal paper"],
        "Fahmida Sultana":        ["Open to public health research collaboration", "Looking for co-author"],
        "Kamrul Hasan":           ["Looking for epidemiology co-author", "Open to health data collaboration"],
        "Tanvir Ahmed Bhuiyan":   ["Seeking industry data collaboration", "Looking for co-author in manufacturing AI"],
        "Md. Mehedi Kibria Jr.":  ["Open to supply chain collaboration", "Looking for industry partner"],
        "Sadia Islam Mim":        ["Looking for partner in additive manufacturing research", "Open to collaboration"],
        "Hasibul Haque":          ["Looking for GIS or remote sensing partner", "Open to climate research collaboration"],
        "Tania Begum":            ["Looking for partner in air quality ML", "Open to environmental data collaboration"],
        "Raihan Kabir":           ["Looking for ML partner for materials discovery", "Open to cross-disciplinary collaboration"],
        "Sumaya Khanam":          ["Looking for quantum computing collaborator", "Open to research partnership"],
        "Aminul Islam Chowdhury": ["Looking for partner in drug discovery AI", "Seeking bioinformatics collaborator"],
        "Protik Das":             ["Looking for partner in financial ML", "Open to data collaboration"],
        "Lamia Sharmin":          ["Looking for business analytics co-author", "Open to industry collaboration"],
        "Towhid Hossain":         ["Looking for food science AI partner", "Open to industry collaboration"],
        "Sohel Rana":             ["Looking for partner in scientific ML", "Open to physics-informed neural network collaboration"],
        "Mariam Akter":           ["Looking for optimization research partner", "Open to healthcare operations collaboration"],
        "Faisal Ahmed":           ["Looking for partner in petroleum ML", "Open to industry data collaboration"],
    }

    with get_conn() as con:
        for row in phd_data:
            cur = con.execute(
                "INSERT INTO phd_students (name,email,university,department,supervisor,research_area,bio,year_enrolled) VALUES (?,?,?,?,?,?,?,?)",
                row
            )
            phd_id = cur.lastrowid
            for tag in tag_map.get(row[0], []):
                con.execute("INSERT INTO phd_student_tags (phd_student_id, tag) VALUES (?,?)", (phd_id, tag))
        con.commit()
    print(f"Seeded {len(phd_data)} PhD students")


# ── Demo student accounts (dummy data for the home feed) ──────────────────

def _seed_demo_students():
    """Seed ~12 demo students with interests, tags and posts so the home
    feed has content. Skipped if demo accounts already exist."""
    with get_conn() as con:
        existing = con.execute(
            "SELECT COUNT(*) FROM students WHERE email LIKE '%@student.sust.edu'"
        ).fetchone()[0]
        if existing:
            print(f"  Demo students already seeded ({existing}) — skipping.")
            return

    # (name, email, dept, year, interests, bio, tags, posts)
    # posts: (title, content, type, days_ago)
    demo = [
        ("Nusrat Jahan", "nusrat@student.sust.edu", "CSE", "3rd Year",
         "Machine Learning, Bangla NLP, Text Mining",
         "CSE undergrad exploring low-resource NLP. Currently obsessed with tokenizers.",
         ["Looking for research partner in NLP", "Seeking thesis partner"],
         [("Built a Bangla sentiment analysis model on 50k Facebook comments",
           "Fine-tuned BanglaBERT and got 87% F1. Happy to share the cleaned dataset if anyone is working on Bangla social media text.",
           "work", 2),
          ("Reading up on transformer fine-tuning tricks",
           "LoRA vs full fine-tuning for small Bangla corpora — if you have experience with either, would love to compare notes.",
           "interest", 9)]),
        ("Tanvir Hasan", "tanvir.h@student.sust.edu", "CSE", "4th Year",
         "Computer Vision, Deep Learning, Medical Imaging",
         "Final-year thesis on medical image analysis. Kaggle addict.",
         ["Looking for research partner in Computer Vision", "Looking for co-author"],
         [("Chest X-ray pneumonia detection — thesis progress",
           "Trained an EfficientNet-B3 on the RSNA dataset, currently at 0.91 AUC. Struggling with class imbalance — tips welcome.",
           "project", 1),
          ("Won silver in a Kaggle medical imaging competition",
           "Team of three, segmentation task on CT scans. Ask me anything about the pipeline.",
           "work", 14)]),
        ("Sadia Afrin", "sadia.a@student.sust.edu", "CSE", "Masters",
         "NLP, Large Language Models, Retrieval-Augmented Generation",
         "Masters student benchmarking RAG pipelines for Bangla question answering.",
         ["Looking for research partner in NLP", "Open to research collaboration"],
         [("Comparing RAG pipelines for Bangla QA",
           "Evaluated 4 retrieval setups on a custom Bangla Wikipedia benchmark. Hybrid BM25 + dense retrieval wins by a wide margin.",
           "work", 3),
          ("AWS Machine Learning Specialty — certified",
           "Took about 6 weeks of prep alongside coursework. Happy to share my notes and practice resources.",
           "certification", 21)]),
        ("Fahim Rahman", "fahim.r@student.sust.edu", "EEE", "4th Year",
         "IoT, Embedded Systems, Smart Grid",
         "Building cheap sensors for real problems. ESP32 evangelist.",
         ["Looking for research partner in IoT", "Looking for industry partner"],
         [("Smart energy meter prototype working!",
           "ESP32 + current clamp + MQTT dashboard, total cost under 1500 taka. Next step: anomaly detection on usage patterns.",
           "project", 4)]),
        ("Maliha Chowdhury", "maliha.c@student.sust.edu", "STA", "Masters",
         "Time Series Forecasting, Climate Data, Machine Learning",
         "Statistics masters student working on flood forecasting for Sylhet haors.",
         ["Open to research collaboration", "Looking for co-author"],
         [("LSTM vs SARIMA for flood forecasting — surprising results",
           "On BWDB water-level data, a well-tuned SARIMA beat my LSTM on 7-day horizon. Writing this up — looking for a co-author with ML background.",
           "work", 5)]),
        ("Rakib Uddin", "rakib.u@student.sust.edu", "CSE", "3rd Year",
         "Cybersecurity, Network Security, Anomaly Detection",
         "Blue-team enthusiast. CTF player on weekends.",
         ["Open to research collaboration"],
         [("Exploring graph neural networks for intrusion detection",
           "Reading the recent literature on GNN-based IDS. If anyone has network flow datasets or works in this area, let's talk.",
           "interest", 6)]),
        ("Farhana Akter", "farhana.a@student.sust.edu", "CSE", "Masters",
         "Bioinformatics, Genomics, Deep Learning",
         "Computational biology fan — proteins are just very confusing strings.",
         ["Looking for research partner in Bioinformatics"],
         [("Mini-review: deep learning for protein structure prediction",
           "Wrote a 10-page review of AlphaFold-style methods for our journal club. DM if you want the PDF.",
           "work", 8)]),
        ("Shakil Ahmed", "shakil.a@student.sust.edu", "CSE", "4th Year",
         "Computer Vision, Edge AI, Robotics",
         "Robotics club lead. I make cameras think on tiny chips.",
         ["Available for project collaboration", "Looking for industry partner"],
         [("Vision-based line follower — 2nd place at robotics fest",
           "Raspberry Pi Zero + quantized MobileNet, full lap in 42 seconds. Code is on my GitHub.",
           "project", 7),
          ("TensorFlow Developer Certificate",
           "Finally done with it. The image classification section is very doable if you have used Keras before.",
           "certification", 25)]),
        ("Tasnim Rahman", "tasnim.r@student.sust.edu", "IPE", "Masters",
         "Operations Research, Optimization, Supply Chain",
         "IPE grad student. I optimize things that don't want to be optimized.",
         ["Open to research collaboration"],
         [("Won the inter-university hackathon with a vehicle routing solver",
           "OR-Tools + a custom heuristic for last-mile delivery in Dhaka traffic. The judges liked the cost dashboard the most.",
           "work", 10)]),
        ("Mehjabin Khan", "mehjabin.k@student.sust.edu", "CSE", "2nd Year",
         "Web Development, Machine Learning, Data Visualization",
         "Second-year student learning ML by building dashboards nobody asked for.",
         ["Available for project collaboration"],
         [("Interactive dashboard of SUST admission statistics",
           "Built with Plotly + Streamlit from public data. Looking for ideas on what campus dataset to visualize next.",
           "project", 11)]),
        ("Arnob Das", "arnob.d@student.sust.edu", "PHY", "Masters",
         "Quantum Computing, Computational Physics",
         "Physics masters student simulating small quantum systems on big classical machines.",
         ["Open to research collaboration"],
         [("Completed Qiskit Global Summer School",
           "Two intense weeks of quantum machine learning. The variational circuits lab was the highlight.",
           "certification", 13)]),
        ("Lamia Hossain", "lamia.h@student.sust.edu", "CSE", "Masters",
         "Human-Computer Interaction, Accessibility, Machine Learning",
         "HCI researcher-in-training. Technology should work for everyone.",
         ["Looking for co-author", "Open to research collaboration"],
         [("Usability study: screen readers on Bangla government websites",
           "Ran a 12-participant study — results are honestly grim. Preparing a paper; need a co-author comfortable with statistics.",
           "work", 12)]),
    ]

    with get_conn() as con:
        for name, email, dept, year, interests, bio, tags, posts in demo:
            salt = secrets.token_hex(16)
            cur = con.execute(
                "INSERT INTO students (name,email,password_hash,salt,university,department,year,bio,research_interests) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (name, email, _hash_password("demo123", salt), salt,
                 "SUST", dept, year, bio, interests))
            sid = cur.lastrowid
            for tag in tags:
                con.execute("INSERT INTO student_tags (student_id,tag) VALUES (?,?)", (sid, tag))
            for title, content, ptype, days_ago in posts:
                con.execute(
                    "INSERT INTO student_posts (student_id,title,content,post_type,created_at) "
                    "VALUES (?,?,?,?,datetime('now', ?))",
                    (sid, title, content, ptype, f"-{days_ago} days"))
        con.commit()
    print(f"Seeded {len(demo)} demo students with posts")


# ── Auth ──────────────────────────────────────────────────────────────────

def signup(name, email, password, university="SUST", department="", year=""):
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    try:
        with get_conn() as con:
            con.execute(
                "INSERT INTO students (name,email,password_hash,salt,university,department,year) VALUES (?,?,?,?,?,?,?)",
                (name, email, pw_hash, salt, university, department, year)
            )
            con.commit()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "Email already registered"}


def login(email, password):
    with get_conn() as con:
        row = con.execute("SELECT * FROM students WHERE email=?", (email,)).fetchone()
    if not row:
        return {"ok": False, "error": "No account with that email"}
    if _hash_password(password, row["salt"]) != row["password_hash"]:
        return {"ok": False, "error": "Incorrect password"}
    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    with get_conn() as con:
        con.execute("INSERT INTO sessions (token,student_id,expires_at) VALUES (?,?,?)",
                    (token, row["id"], expires))
        con.commit()
    return {"ok": True, "token": token, "student_id": row["id"], "name": row["name"]}


def verify_token(token):
    with get_conn() as con:
        row = con.execute("SELECT * FROM sessions WHERE token=?", (token,)).fetchone()
    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        with get_conn() as con:
            con.execute("DELETE FROM sessions WHERE token=?", (token,))
            con.commit()
        return None
    return int(row["student_id"])


def logout(token):
    with get_conn() as con:
        con.execute("DELETE FROM sessions WHERE token=?", (token,))
        con.commit()


# ── Student profile ───────────────────────────────────────────────────────

def get_student(student_id):
    with get_conn() as con:
        row = con.execute(
            "SELECT id,name,email,university,department,year,bio,"
            "research_interests,research_summary,cv_filename,photo_data,photo_mime "
            "FROM students WHERE id=?",
            (student_id,)
        ).fetchone()
        if not row:
            return None
        student = dict(row)
        photo = student.pop("photo_data", None)
        student["photo_b64"] = base64.b64encode(photo).decode() if photo else None
        student["tags"]  = [dict(r) for r in con.execute(
            "SELECT id,tag FROM student_tags WHERE student_id=? ORDER BY created_at DESC", (student_id,)
        ).fetchall()]
        student["posts"] = []
        for r in con.execute(
            "SELECT id,title,content,post_type,created_at,image_data,image_mime "
            "FROM student_posts WHERE student_id=? ORDER BY created_at DESC",
            (student_id,)
        ).fetchall():
            p = dict(r)
            img = p.pop("image_data", None)
            p["image_b64"] = base64.b64encode(img).decode() if img else None
            student["posts"].append(p)
        student["documents"] = [dict(r) for r in con.execute(
            "SELECT id,filename,label,mime,uploaded_at,LENGTH(data) AS size "
            "FROM student_documents WHERE student_id=? ORDER BY uploaded_at DESC",
            (student_id,)
        ).fetchall()]
    return student


def update_student(student_id, bio=None, university=None, department=None, year=None,
                   research_interests=None, research_summary=None):
    fields, vals = [], []
    if bio is not None:                fields.append("bio=?");                vals.append(bio)
    if university is not None:         fields.append("university=?");         vals.append(university)
    if department is not None:         fields.append("department=?");         vals.append(department)
    if year is not None:               fields.append("year=?");               vals.append(year)
    if research_interests is not None: fields.append("research_interests=?"); vals.append(research_interests)
    if research_summary is not None:   fields.append("research_summary=?");   vals.append(research_summary)
    if not fields:
        return
    vals.append(student_id)
    with get_conn() as con:
        con.execute(f"UPDATE students SET {', '.join(fields)} WHERE id=?", vals)
        con.commit()


# ── CV upload/download ─────────────────────────────────────────────────────

def save_cv(student_id, filename, data: bytes):
    with get_conn() as con:
        con.execute("UPDATE students SET cv_filename=?, cv_data=? WHERE id=?",
                    (filename, data, student_id))
        con.commit()


def get_cv(student_id):
    with get_conn() as con:
        row = con.execute(
            "SELECT cv_filename, cv_data FROM students WHERE id=?", (student_id,)
        ).fetchone()
    if not row or not row["cv_data"]:
        return None
    return row["cv_filename"], row["cv_data"]


def delete_cv(student_id):
    with get_conn() as con:
        con.execute("UPDATE students SET cv_filename='', cv_data=NULL WHERE id=?",
                    (student_id,))
        con.commit()


# ── Profile photo ──────────────────────────────────────────────────────────

def save_photo(student_id, data: bytes, mime: str):
    with get_conn() as con:
        con.execute("UPDATE students SET photo_data=?, photo_mime=? WHERE id=?",
                    (data, mime, student_id))
        con.commit()


def get_photo(student_id):
    with get_conn() as con:
        row = con.execute("SELECT photo_data, photo_mime FROM students WHERE id=?",
                          (student_id,)).fetchone()
    if not row or not row["photo_data"]:
        return None
    return row["photo_data"], row["photo_mime"] or "image/jpeg"


def delete_photo(student_id):
    with get_conn() as con:
        con.execute("UPDATE students SET photo_data=NULL, photo_mime='' WHERE id=?",
                    (student_id,))
        con.commit()


# ── Documents (LinkedIn-style attachments) ─────────────────────────────────

def add_document(student_id, filename, label, mime, data: bytes):
    with get_conn() as con:
        con.execute(
            "INSERT INTO student_documents (student_id,filename,label,mime,data) VALUES (?,?,?,?,?)",
            (student_id, filename, label, mime, data))
        con.commit()


def get_document(doc_id):
    with get_conn() as con:
        row = con.execute(
            "SELECT student_id, filename, mime, data FROM student_documents WHERE id=?",
            (doc_id,)).fetchone()
    return dict(row) if row else None


def delete_document(doc_id, student_id):
    with get_conn() as con:
        con.execute("DELETE FROM student_documents WHERE id=? AND student_id=?",
                    (doc_id, student_id))
        con.commit()


# ── Home feed — posts from students with overlapping interests ─────────────

_FEED_STOP = {
    "in", "on", "of", "to", "at", "is", "as", "an", "or", "be", "by", "my",
    "we", "if", "it", "do", "up", "so", "am", "me", "the", "and", "for",
    "with", "from", "using", "based", "into", "about", "this", "that", "are",
    "was", "has", "have", "had", "not", "but", "you", "your", "our", "his",
    "her", "its", "them", "they", "one", "two", "next", "new", "also", "very",
    "open", "looking", "seeking", "research", "partner", "collaboration",
    "student", "students", "interested", "interests", "area", "areas",
    "work", "working", "currently", "exploring", "reading", "building",
    "thesis", "paper", "project", "projects", "study", "results",
}


def _keywords(text: str) -> set:
    words = re.findall(r"[a-zA-Z]{2,}", (text or "").lower())
    return {w for w in words if w not in _FEED_STOP}


def get_feed(student_id, limit=20):
    """Posts by other students, ranked by keyword overlap between the viewer's
    interests/tags/bio and each author's interests/tags (plus the post text)."""
    with get_conn() as con:
        me = con.execute(
            "SELECT research_interests, bio FROM students WHERE id=?",
            (student_id,)).fetchone()
        if not me:
            return []
        my_tags = [r["tag"] for r in con.execute(
            "SELECT tag FROM student_tags WHERE student_id=?", (student_id,)).fetchall()]
        my_kw = _keywords(" ".join(filter(None, [me["research_interests"], me["bio"], *my_tags])))
        my_phrases = [p.strip() for p in (me["research_interests"] or "").split(",") if p.strip()]

        posts = con.execute("""
            SELECT p.id, p.title, p.content, p.post_type, p.created_at,
                   p.image_data, p.image_mime,
                   s.id AS author_id, s.name AS author_name, s.department,
                   s.university, s.year, s.research_interests,
                   s.photo_data, s.photo_mime
            FROM student_posts p
            JOIN students s ON s.id = p.student_id
            WHERE p.student_id != ?
            ORDER BY p.created_at DESC
            LIMIT 300
        """, (student_id,)).fetchall()

        tags_by = defaultdict(list)
        for r in con.execute("SELECT student_id, tag FROM student_tags").fetchall():
            tags_by[r["student_id"]].append(r["tag"])

    def _display_matches(shared: set) -> list:
        """Show the viewer's own interest phrases ('Machine Learning') that
        overlap, falling back to raw shared words if none do."""
        hits = [p for p in my_phrases if _keywords(p) & shared]
        if hits:
            return hits[:3]
        return [w.title() for w in sorted(shared)[:3]]

    items = []
    for r in posts:
        author_kw = _keywords(" ".join(filter(None, [r["research_interests"], *tags_by[r["author_id"]]])))
        post_kw   = _keywords(f"{r['title']} {r['content'] or ''}")
        shared    = my_kw & (author_kw | post_kw)
        items.append({
            "post_id":     r["id"],
            "title":       r["title"],
            "content":     r["content"] or "",
            "post_type":   r["post_type"],
            "created_at":  r["created_at"],
            "image_b64":   base64.b64encode(r["image_data"]).decode() if r["image_data"] else None,
            "image_mime":  r["image_mime"] or "image/jpeg",
            "match_score": len(shared),
            "matched":     _display_matches(shared) if shared else [],
            "author": {
                "id":         r["author_id"],
                "name":       r["author_name"],
                "department": r["department"] or "",
                "university": r["university"] or "",
                "year":       r["year"] or "",
                "interests":  r["research_interests"] or "",
                "photo_b64":  base64.b64encode(r["photo_data"]).decode() if r["photo_data"] else None,
                "photo_mime": r["photo_mime"] or "image/jpeg",
            },
        })

    items.sort(key=lambda i: i["created_at"], reverse=True)
    items.sort(key=lambda i: i["match_score"], reverse=True)
    return items[:limit]


# ── Posts ──────────────────────────────────────────────────────────────────

def add_post(student_id, title, content, post_type="work",
             image_data=None, image_mime=""):
    with get_conn() as con:
        con.execute(
            "INSERT INTO student_posts (student_id,title,content,post_type,image_data,image_mime) "
            "VALUES (?,?,?,?,?,?)",
            (student_id, title, content, post_type, image_data, image_mime)
        )
        con.commit()


def delete_post(post_id, student_id):
    with get_conn() as con:
        con.execute("DELETE FROM student_posts WHERE id=? AND student_id=?", (post_id, student_id))
        con.commit()


# ── Tags ───────────────────────────────────────────────────────────────────

def add_tag(student_id, tag):
    with get_conn() as con:
        con.execute("INSERT INTO student_tags (student_id,tag) VALUES (?,?)", (student_id, tag))
        con.commit()


def delete_tag(tag_id, student_id):
    with get_conn() as con:
        con.execute("DELETE FROM student_tags WHERE id=? AND student_id=?", (tag_id, student_id))
        con.commit()


# ── Save faculty ──────────────────────────────────────────────────────────

def save_faculty(student_id, faculty_id):
    try:
        with get_conn() as con:
            con.execute("INSERT INTO student_saved_faculty (student_id,faculty_id) VALUES (?,?)",
                        (student_id, faculty_id))
            con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def unsave_faculty(student_id, faculty_id):
    with get_conn() as con:
        con.execute("DELETE FROM student_saved_faculty WHERE student_id=? AND faculty_id=?",
                    (student_id, faculty_id))
        con.commit()


def get_saved_faculty(student_id):
    with get_conn() as con:
        rows = con.execute("""
            SELECT f.id, f.name, f.designation, f.department, f.email, f.profile_url
            FROM faculty f
            JOIN student_saved_faculty sf ON f.id = sf.faculty_id
            WHERE sf.student_id=?
            ORDER BY sf.added_at DESC
        """, (student_id,)).fetchall()
    return [dict(r) for r in rows]


def get_saved_faculty_ids(student_id):
    with get_conn() as con:
        return [r[0] for r in con.execute(
            "SELECT faculty_id FROM student_saved_faculty WHERE student_id=?", (student_id,)
        ).fetchall()]


# ── Save PhD student (sample data) ────────────────────────────────────────

def save_phd(student_id, phd_student_id):
    try:
        with get_conn() as con:
            con.execute("INSERT INTO student_saved_phd (student_id,phd_student_id) VALUES (?,?)",
                        (student_id, phd_student_id))
            con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def unsave_phd(student_id, phd_student_id):
    with get_conn() as con:
        con.execute("DELETE FROM student_saved_phd WHERE student_id=? AND phd_student_id=?",
                    (student_id, phd_student_id))
        con.commit()


def get_saved_phd(student_id):
    with get_conn() as con:
        rows = con.execute("""
            SELECT p.id, p.name, p.university, p.department, p.supervisor, p.research_area, p.email
            FROM phd_students p
            JOIN student_saved_phd sp ON p.id = sp.phd_student_id
            WHERE sp.student_id=?
            ORDER BY sp.added_at DESC
        """, (student_id,)).fetchall()
    return [dict(r) for r in rows]


def get_saved_phd_ids(student_id):
    with get_conn() as con:
        return [r[0] for r in con.execute(
            "SELECT phd_student_id FROM student_saved_phd WHERE student_id=?", (student_id,)
        ).fetchall()]


# ── Save registered student ───────────────────────────────────────────────

def save_student_contact(student_id, target_student_id):
    if student_id == target_student_id:
        return False
    try:
        with get_conn() as con:
            con.execute(
                "INSERT INTO student_saved_students (student_id,target_student_id) VALUES (?,?)",
                (student_id, target_student_id)
            )
            con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def unsave_student_contact(student_id, target_student_id):
    with get_conn() as con:
        con.execute(
            "DELETE FROM student_saved_students WHERE student_id=? AND target_student_id=?",
            (student_id, target_student_id)
        )
        con.commit()


def get_saved_student_contacts(student_id):
    with get_conn() as con:
        rows = con.execute("""
            SELECT s.id, s.name, s.university, s.department, s.bio, s.email
            FROM students s
            JOIN student_saved_students ss ON s.id = ss.target_student_id
            WHERE ss.student_id=?
            ORDER BY ss.added_at DESC
        """, (student_id,)).fetchall()
        results = []
        for row in rows:
            r = dict(row)
            tags = con.execute(
                "SELECT tag FROM student_tags WHERE student_id=? ORDER BY created_at DESC LIMIT 5",
                (r["id"],)
            ).fetchall()
            r["tags"] = [t[0] for t in tags]
            results.append(r)
    return results


def get_saved_student_ids(student_id):
    with get_conn() as con:
        return [r[0] for r in con.execute(
            "SELECT target_student_id FROM student_saved_students WHERE student_id=?", (student_id,)
        ).fetchall()]


# ── PhD student search ─────────────────────────────────────────────────────

def _attach_phd_tags(con, rows):
    results = []
    for row in rows:
        s = dict(row)
        tags = con.execute(
            "SELECT id, tag FROM phd_student_tags WHERE phd_student_id=?", (s["id"],)
        ).fetchall()
        s["tags"] = [{"id": t["id"], "tag": t["tag"]} for t in tags]
        s["source"] = "phd"
        results.append(s)
    return results


def _attach_student_tags(con, rows):
    results = []
    for row in rows:
        s = dict(row)
        tags = con.execute(
            "SELECT id, tag FROM student_tags WHERE student_id=?", (s["id"],)
        ).fetchall()
        s["tags"] = [{"id": t["id"], "tag": t["tag"]} for t in tags]
        s["source"] = "student"
        s.setdefault("supervisor", "")
        s.setdefault("year_enrolled", s.get("year", ""))
        results.append(s)
    return results


def get_phd_student(phd_id: int):
    with get_conn() as con:
        row = con.execute(
            "SELECT id,name,email,university,department,supervisor,research_area,bio,year_enrolled FROM phd_students WHERE id=?",
            (phd_id,)
        ).fetchone()
        if not row:
            return None
        s = dict(row)
        tags = con.execute("SELECT id,tag FROM phd_student_tags WHERE phd_student_id=?", (phd_id,)).fetchall()
        s["tags"] = [{"id": t["id"], "tag": t["tag"]} for t in tags]
    return s


def search_phd_students(query: str):
    q = f"%{query}%"
    with get_conn() as con:
        phd_rows = con.execute("""
            SELECT DISTINCT p.id, p.name, p.email, p.university, p.department,
                            p.supervisor, p.research_area, p.bio, p.year_enrolled
            FROM phd_students p
            LEFT JOIN phd_student_tags t ON p.id = t.phd_student_id
            WHERE p.name LIKE ? OR p.research_area LIKE ? OR p.bio LIKE ?
               OR p.department LIKE ? OR t.tag LIKE ?
        """, (q, q, q, q, q)).fetchall()

        student_rows = con.execute("""
            SELECT DISTINCT s.id, s.name, s.email, s.university, s.department,
                            s.bio, s.year
            FROM students s
            INNER JOIN student_tags st ON s.id = st.student_id
            WHERE s.name LIKE ? OR s.bio LIKE ? OR s.department LIKE ? OR st.tag LIKE ?
        """, (q, q, q, q)).fetchall()

        results = _attach_phd_tags(con, phd_rows) + _attach_student_tags(con, student_rows)
    return results


def get_all_phd_students():
    with get_conn() as con:
        phd_rows = con.execute(
            "SELECT id,name,email,university,department,supervisor,research_area,bio,year_enrolled FROM phd_students ORDER BY name"
        ).fetchall()

        student_rows = con.execute("""
            SELECT DISTINCT s.id, s.name, s.email, s.university, s.department, s.bio, s.year
            FROM students s
            INNER JOIN student_tags st ON s.id = st.student_id
            ORDER BY s.name
        """).fetchall()

        results = _attach_phd_tags(con, phd_rows) + _attach_student_tags(con, student_rows)
    return results
