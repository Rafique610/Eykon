"""Benchmark dataset — 500 memories of a Pakistani CS university student + 30 QA pairs.

The student is a 4th-year CS major. Key facts woven consistently throughout:
  Roommate    : Hassan (from Multan, gamer)
  Best friend : Omar (met in Prog Fundamentals, calm, punctual)
  Friends     : Zara (top Algo student), Bilal from EE (cricket)
  Profs       : Sir Imran (DS + FYP supervisor), Mam Ayesha (Algo, strict),
                Sir Zafar (OOP), Mam Saba (Linear Algebra), Sir Hassan (Networks)
  FYP         : Medical Image Classification — pneumonia in chest X-rays
  Stack       : Python, TensorFlow, Keras, Google Colab, ChestX-ray14
  Hostel      : Iqbal Hostel, Room 215, 2nd floor
  CGPA        : 3.2 / 4.0   |   Allowance: PKR 15 000/month
  Bus         : 7:30 AM from hostel stop
"""
from __future__ import annotations

# ── Gold memories (50) ──────────────────────────────────────────────────────
# Format: (key, text)
# key  → used by QA pairs to locate the relevant chunk after insertion.
# text → some are intentionally long (>256 tokens) so they will be chunked.

GOLD_MEMORIES: list[tuple[str, str]] = [
    # ── Morning / routine ────────────────────────────────────────────────────
    ("wake_up_time",
     "I wake up at 6:45 AM on weekdays to catch the 7:30 AM shuttle bus. "
     "I set three alarms but always end up waking to the third one. "
     "Hassan, my roommate, somehow manages to wake up even later than me "
     "and still makes it to his classes, which I find both impressive and infuriating."),

    ("morning_routine",
     "My morning routine is extremely rushed. I brush my teeth, splash cold water "
     "on my face, grab my backpack, and sprint to the bus stop. I almost never "
     "have time to eat breakfast before class. By 11 AM I am usually starving "
     "and regret not keeping biscuits in my bag."),

    # ── Classes ──────────────────────────────────────────────────────────────
    ("class_ds",
     "My Data Structures class is every Monday, Wednesday, and Friday at 8:00 AM "
     "in room CS-101. Sir Imran never delays the lecture even by a single minute, "
     "so being late means missing key definitions. It is the earliest class of my "
     "week and the one I find most difficult to attend on time."),

    ("class_algo",
     "I have Algorithms on Tuesday and Thursday at 10:00 AM in Lab-3. "
     "The professor uses a digital attendance system so I cannot fake being present. "
     "The lab has whiteboards on three walls which she fills entirely with proofs "
     "by the end of every session. I photograph them before leaving."),

    ("class_networks",
     "Computer Networks meets on Wednesday at 2:00 PM in room CS-204. "
     "It is my only afternoon class during the week. "
     "The professor uses real Wireshark packet captures to show how protocols "
     "behave in practice, which makes the content much more concrete."),

    ("class_linear_algebra",
     "Linear Algebra runs every Tuesday, Thursday, and Saturday at 9:00 AM. "
     "The Saturday morning slot is the hardest to attend, especially in winter "
     "when the hostel blanket is much more inviting than a 9 AM derivation lecture."),

    ("class_oop",
     "My OOP class is Monday and Wednesday at 12:00 PM in room CS-102. "
     "The professor writes very clean code examples on the board and requires "
     "us to follow SOLID principles even in lab exercises. "
     "It is one of the more well-organised courses this semester."),

    ("class_se",
     "Software Engineering is Friday at 11:00 AM. The professor emphasises agile "
     "methodology and we run weekly scrum stand-ups as part of our lab grade. "
     "It is the most practically oriented course in my current semester."),

    # ── Professors ───────────────────────────────────────────────────────────
    ("prof_imran",
     "Sir Imran teaches Data Structures and is also my FYP supervisor. "
     "He is demanding but completely fair. He always says that if you cannot explain "
     "a concept simply, you do not truly understand it. He holds office hours every "
     "Tuesday from 3 to 5 PM and is consistently available for FYP guidance discussions."),

    ("prof_ayesha",
     "Mam Ayesha teaches Algorithms and she is the strictest professor I have. "
     "She gave me a B-plus last semester and called me out in class once for not "
     "being able to prove the time complexity of a sorting algorithm on the spot. "
     "That embarrassment pushed me to study far more rigorously this term."),

    ("prof_zafar",
     "Sir Zafar teaches Object Oriented Programming. He has industry experience "
     "at a fintech startup and often shares war stories from that time. "
     "He once praised my class design in front of the whole lecture hall, "
     "which was a genuinely proud moment for me."),

    ("prof_saba",
     "Mam Saba teaches Linear Algebra. She is patient and soft-spoken, which is a "
     "welcome contrast to how difficult the subject itself is. Many students failed "
     "last semester but her teaching is very structured if you actually do the "
     "practice problems she assigns after each class."),

    ("prof_hassan_net",
     "Sir Hassan teaches Computer Networks. He spent eight years at a Pakistani "
     "telecom company before moving to academia. His professional background means "
     "every lecture has very relevant, real-world examples drawn from actual "
     "network incidents he dealt with professionally."),

    # ── Friends and social ───────────────────────────────────────────────────
    ("roommate",
     "My roommate is Hassan. He is from Multan and is also in the CS program. "
     "His gaming setup takes up a large portion of the room. We generally get along "
     "well except when he plays Valorant late at night with his headset on and "
     "the mechanical keyboard clicking keeps me awake while I am trying to sleep."),

    ("best_friend",
     "My best friend at university is Omar. We met during the very first week "
     "in the Programming Fundamentals lab and have been inseparable since. "
     "He is sharp, consistently punctual, and always calm before exams "
     "while I am quietly panicking next to him."),

    ("friend_zara",
     "Zara is a classmate from Algorithms who consistently ranks near the top. "
     "When I am stuck on an assignment problem I message her first. "
     "She explains things without making you feel stupid for not knowing, "
     "which is a rare quality and something I genuinely appreciate."),

    ("study_group",
     "For major exams I study with Omar and Zara. Omar handles algorithmic thinking "
     "problems and Zara is expert at mathematical proofs and derivations. "
     "Together we quiz each other on every section until all three of us feel "
     "confident enough to walk into the exam hall without anxiety."),

    ("library_spot",
     "Our preferred study spot is the corner table on the second floor of the "
     "university library. It has good natural light, it is far from the main "
     "entrance so foot traffic is minimal, and there is a power socket right "
     "next to the table for charging all three of our laptops simultaneously."),

    ("friend_bilal_ee",
     "There is another Bilal in the Electrical Engineering department. "
     "We do not share any classes but we play cricket together every Saturday. "
     "He is an excellent fielder and insists, usually while fielding, "
     "that EE students are naturally more athletic than CS students."),

    # ── FYP ──────────────────────────────────────────────────────────────────
    ("fyp_topic",
     "My Final Year Project is a Medical Image Classification system. "
     "I am building a deep learning model to detect pneumonia from chest X-ray images. "
     "The goal is to produce a model accurate enough to genuinely assist radiologists "
     "working in under-resourced public hospitals across Pakistan."),

    ("fyp_tools",
     "My FYP is built in Python using TensorFlow and Keras as the deep learning "
     "framework. I run all training on Google Colab because my laptop overheats "
     "during long training jobs. The dataset is ChestX-ray14 from the National "
     "Institutes of Health, which contains over 100,000 chest X-ray images with "
     "disease labels verified by radiologists."),

    ("fyp_progress",
     "This week my model reached 87 percent validation accuracy on the chest X-ray "
     "dataset. My supervisor reviewed the results and said he wants to see the model "
     "break 90 percent before the next milestone review. He recommended trying "
     "data augmentation and label smoothing as the next experiment to run."),

    ("fyp_deadline",
     "The final FYP submission deadline is in March next year. Before that I need "
     "a working live demo and a complete written report. My supervisor conducts a "
     "progress review every two weeks and expects a new results table at each meeting. "
     "The pressure is real but manageable as long as I stay consistent."),

    # ── Hostel ───────────────────────────────────────────────────────────────
    ("hostel_name",
     "I live in Iqbal Hostel on campus. It is the closest hostel to the CS "
     "department building, which means I can walk to my first class in under "
     "five minutes. Despite that geographical advantage, I still sometimes "
     "manage to be late, which is a personal failure I am working on."),

    ("hostel_room",
     "My room number is 215, placing me on the second floor. The room has two beds, "
     "two study desks pushed against opposite walls, and a small window that looks "
     "directly onto the hostel cricket ground. On match days the crowd noise coming "
     "through the window is simultaneously distracting and entertaining."),

    # ── Food ─────────────────────────────────────────────────────────────────
    ("lunch_spot",
     "I usually eat lunch at the university cafeteria. My go-to meal is daal chawal, "
     "which costs 80 rupees and is genuinely filling. On days when the cafeteria "
     "food is particularly bad or I want a change, Omar and I walk to the dhaba "
     "just outside the main campus gate instead."),

    ("food_biryani",
     "The dhaba just outside the main campus gate serves the best biryani in the "
     "area. Omar and I make a point of going at least once a week. A generous portion "
     "costs 150 rupees. It has slowly become a weekly ritual between us, "
     "something we both look forward to regardless of how the week is going."),

    ("food_habits",
     "I almost never eat breakfast because my morning routine leaves absolutely no "
     "time for it. Lunch is the main meal of my day. I also buy a samosa or bun "
     "kebab from the canteen stall in the afternoon as a snack even though I know "
     "it is far from healthy. Old habits are genuinely hard to break."),

    # ── Finance ──────────────────────────────────────────────────────────────
    ("allowance",
     "My family sends me 15,000 rupees every month as my living allowance. "
     "After hostel food charges, transport, and internet, I am usually down to "
     "2,000 or 3,000 rupees by the last week of the month. It is enough but "
     "there is very little room for anything extra or unexpected."),

    ("expenses",
     "My largest monthly expense is the hostel cafeteria plan, which comes to roughly "
     "7,000 rupees. After that, transport, phone credit, and occasional printing fees "
     "for assignment reports eat through the rest. Saving anything meaningful "
     "at the end of the month is extremely difficult on this budget."),

    # ── CGPA and grades ──────────────────────────────────────────────────────
    ("cgpa",
     "My current CGPA is 3.2 out of 4.0. I am aiming to raise it to at least 3.5 "
     "before graduation. My strongest semester was the very first one when I was "
     "fresh, motivated, and managed to get A grades in two subjects "
     "before the reality of upper-division courses set in."),

    ("worst_grade",
     "My worst grade ever was a C in Linear Algebra last semester. "
     "It is the lowest mark I have received since starting university. "
     "The final exam caught me badly underprepared because I had underestimated "
     "how much deliberate practice the derivation problems actually required."),

    ("best_grade",
     "My best grade was an A in Programming Fundamentals in my very first year. "
     "I spent two full days without sleeping before that final exam and it paid off. "
     "Sir Adnan wrote a comment on my answer sheet saying it was one of the best "
     "freshman submissions he had marked in recent years, which I still remember."),

    # ── Transport ────────────────────────────────────────────────────────────
    ("bus_timing",
     "The university shuttle leaves from the stop right next to Iqbal Hostel "
     "every morning at exactly 7:30 AM. The driver does not wait for latecomers "
     "under any circumstances. I have already missed it twice this semester, "
     "which is why I have now set four alarms instead of three."),

    ("rickshaw",
     "When I miss the morning shuttle, my only practical option is a rickshaw. "
     "It costs around 150 rupees and takes about 20 minutes through morning traffic. "
     "The ride is noisy and the suspension is non-existent, but it reliably "
     "gets me to campus in time to avoid missing the first lecture."),

    # ── Sport ────────────────────────────────────────────────────────────────
    ("sport_cricket",
     "I play cricket on the hostel ground every Saturday evening. "
     "I open the batting for our informal team. My personal best score is "
     "43 runs in a match against the Civil Engineering hostel team, "
     "which we won comfortably and celebrated with a trip to the biryani dhaba."),

    ("sport_team",
     "My cricket team consists of Omar, my roommate Hassan, Bilal from "
     "Electrical Engineering, and a handful of other hostel residents who "
     "show up reliably on Saturdays. We practise casually on quiet weekday "
     "evenings and play proper competitive matches on Saturday afternoons."),

    # ── Exams ────────────────────────────────────────────────────────────────
    ("exam_ds_date",
     "My Data Structures midterm exam is this Thursday at 9:00 AM in "
     "Examination Hall B. I have only two evenings of revision time left "
     "and I am already feeling the pressure building. I need to be very "
     "focused and avoid wasting time tonight."),

    ("exam_ds_topics",
     "Sir Imran confirmed the midterm will cover binary trees, min-heaps, "
     "and graph traversal algorithms, specifically breadth-first search and "
     "depth-first search. He mentioned there will be at least one full coding "
     "question where we must implement an algorithm from scratch on paper."),

    # ── Assignments ──────────────────────────────────────────────────────────
    ("assignment_due_net",
     "I have a large assignment due this Friday for one of my core second-half "
     "semester subjects. It involves designing and simulating a complete network "
     "for a fictional multi-department office building, including routing "
     "configuration between all the different floors and departments."),

    ("assignment_tools_net",
     "The network assignment requires Cisco Packet Tracer for simulation. "
     "I need to configure VLANs for each department, set up OSPF dynamic routing, "
     "and then verify end-to-end connectivity using simulated ping tests. "
     "It is the most hands-on and technically demanding assignment I have had "
     "this entire semester and it is taking far longer than I estimated."),

    ("assignment_load",
     "This week I have three separate assignments due at almost the same time: "
     "a full network simulation for Networks, a class design task for OOP, "
     "and a written progress update for my FYP supervisor. I am currently "
     "running on five hours of sleep per night and roughly three cups of tea "
     "per day just to keep functioning at a basic level."),

    # ── Health ───────────────────────────────────────────────────────────────
    ("health_sleep",
     "I average around five to six hours of sleep per night during term time. "
     "I know this is not sustainable or healthy but between classes in the morning, "
     "assignments in the evening, and FYP experiments running overnight on Colab, "
     "there is no realistic path to more sleep without something slipping. "
     "Tea is what keeps me going through the afternoon slump every single day."),

    ("health_sick",
     "I caught a bad fever last week and missed two consecutive days of class. "
     "Even though I submitted a valid medical certificate from the campus clinic, "
     "Mam Ayesha counted both absences as unexcused because she only accepts "
     "certificates from specific approved hospitals. I am now behind on two "
     "Algorithms lectures and need to borrow Zara's notes to catch up properly."),

    # ── Hobbies ──────────────────────────────────────────────────────────────
    ("hobby_gaming",
     "Hassan and I play Valorant together on weekend evenings when assignment "
     "pressure is manageable. He insists I am a bad player but my solo queue "
     "win rate is actually slightly higher than his across the last thirty games, "
     "a fact I bring up frequently and he consistently disputes with excuses."),

    ("hobby_reading",
     "Before sleeping I try to read a few pages of a non-technical book to "
     "wind down. I am currently reading Atomic Habits. The chapter on habit "
     "stacking has given me concrete ideas about how to attach a short revision "
     "block to my existing evening tea routine to build more consistent study habits."),

    # ── Evening routine ──────────────────────────────────────────────────────
    ("evening_routine",
     "My evenings typically start with reviewing lecture notes from the day, "
     "followed by dinner at the cafeteria around 7 PM, and then several hours "
     "of assignment work or FYP experiments running on Colab. I rarely manage "
     "to be in bed before 1 AM, which directly feeds into the morning alarm problem."),

    # ── Long diary entries (intentionally >256 tokens each) ──────────────────
    ("long_entry_monday",
     "Monday was a full and exhausting day from start to finish. "
     "I woke to the third alarm at 6:45 AM as usual, rushed through my minimal "
     "morning routine, grabbed my bag, and made it to the bus stop with about "
     "two minutes to spare before the 7:30 AM shuttle. Data Structures started "
     "at 8:00 AM sharp and Sir Imran dove immediately into AVL tree rotations "
     "without preamble. The derivation of the rotation conditions took the entire "
     "first hour and I filled three pages of notes trying to keep up. "
     "By the time OOP started at noon my hand was already tired. Sir Zafar "
     "introduced the Strategy design pattern using a payment processing example "
     "from his fintech days, which actually made the abstract concept click for me. "
     "Lunch was daal chawal at the cafeteria, eaten quickly between OOP and my "
     "afternoon free period, which I used to start on the Networks assignment. "
     "The OSPF configuration section is taking much longer than expected "
     "because the simulated router commands are slightly different from the "
     "textbook syntax I had memorised. I stayed in the library until 9 PM "
     "before heading back to the hostel for dinner and another two hours of "
     "FYP work before sleeping just past midnight."),

    ("long_entry_exam_week",
     "Exam week for the midterms is the most stressful period of the entire "
     "semester without exception. I have four midterms spread across eight days "
     "and they cover subjects that require completely different types of thinking. "
     "Data Structures needs you to think algorithmically and trace through code "
     "execution step by step. Linear Algebra needs you to internalise transformation "
     "rules and reproduce derivations under time pressure with no margin for error. "
     "Algorithms requires you to produce complexity proofs from first principles. "
     "OOP requires design sense and the ability to apply patterns to novel scenarios. "
     "My approach this time is to study with Omar and Zara in the library every "
     "evening from 6 PM until closing at 10 PM, then continue on my own in the "
     "room until I feel confident enough to sleep without anxiety. "
     "The corner table on the second floor has become our unofficial headquarters "
     "for the week. Zara handles the mathematical derivation heavy lifting and "
     "Omar is consistently the one who spots logical gaps in our reasoning. "
     "I mostly coordinate, make sure we cover all the topics, and provide the "
     "tea runs downstairs to the canteen stall every two hours to keep morale up. "
     "If the three of us maintain this rhythm for the full eight days I am "
     "cautiously optimistic about the results."),

    ("long_entry_fyp_session",
     "I spent five hours on the FYP today and it was one of the more productive "
     "sessions I have had in weeks. I started by loading the ChestX-ray14 dataset "
     "into a fresh Colab notebook and implementing the data augmentation pipeline "
     "that Sir Imran recommended in our last meeting. The augmentations I added "
     "were horizontal flipping, random brightness and contrast adjustment, and "
     "small random rotations of up to ten degrees, which are all realistic "
     "variations that could occur in real clinical X-ray acquisition. "
     "I then retrained the base model for thirty epochs with the augmented data "
     "and the validation accuracy jumped from 87 to 89.3 percent, which is very "
     "encouraging but still just short of the 90 percent milestone target. "
     "I think the remaining gap might be addressable with label smoothing "
     "or a learning rate schedule adjustment. I saved the training logs and "
     "the model checkpoint so I can share them with Sir Imran at our next "
     "bi-weekly meeting on Thursday afternoon. The fact that data augmentation "
     "alone moved the needle by more than two percent in a single training run "
     "suggests the model was overfitting to the training distribution previously, "
     "which is exactly what Sir Imran suspected when he saw the original results."),
]

# ── 30 QA pairs ──────────────────────────────────────────────────────────────
# gold_keys: memory keys whose chunks must appear in top results.
# For multi-hop, a result is counted as a hit if ANY of the gold keys is found
# (partial credit). Full answers need both keys in top-5 for the question to
# be properly answerable — this is noted in the 'notes' field.

QA_PAIRS: list[dict] = [
    # ── Exact recall (10) ────────────────────────────────────────────────────
    {"id": 1,  "question": "What time does my Data Structures class start?",
     "gold_keys": ["class_ds"], "query_type": "exact",
     "notes": "8:00 AM Monday/Wednesday/Friday, CS-101"},

    {"id": 2,  "question": "Who is my roommate?",
     "gold_keys": ["roommate"], "query_type": "exact",
     "notes": "Hassan, from Multan, gamer"},

    {"id": 3,  "question": "What is my current CGPA?",
     "gold_keys": ["cgpa"], "query_type": "exact",
     "notes": "3.2 out of 4.0"},

    {"id": 4,  "question": "What does Sir Imran teach and what is his role in my FYP?",
     "gold_keys": ["prof_imran"], "query_type": "exact",
     "notes": "Data Structures + FYP supervisor"},

    {"id": 5,  "question": "What is my Final Year Project about?",
     "gold_keys": ["fyp_topic"], "query_type": "exact",
     "notes": "Medical image classification, pneumonia detection"},

    {"id": 6,  "question": "Where do I usually eat lunch on campus?",
     "gold_keys": ["lunch_spot"], "query_type": "exact",
     "notes": "University cafeteria, daal chawal 80 rupees"},

    {"id": 7,  "question": "What frameworks and tools am I using for my FYP?",
     "gold_keys": ["fyp_tools"], "query_type": "exact",
     "notes": "Python, TensorFlow, Keras, Colab, ChestX-ray14"},

    {"id": 8,  "question": "How much monthly allowance does my family send me?",
     "gold_keys": ["allowance"], "query_type": "exact",
     "notes": "PKR 15,000 per month"},

    {"id": 9,  "question": "Who is my best friend at university?",
     "gold_keys": ["best_friend"], "query_type": "exact",
     "notes": "Omar, met in Programming Fundamentals lab first year"},

    {"id": 10, "question": "What time does the university shuttle bus leave?",
     "gold_keys": ["bus_timing"], "query_type": "exact",
     "notes": "7:30 AM sharp from near Iqbal Hostel"},

    # ── Semantic inference (10) ───────────────────────────────────────────────
    {"id": 11, "question": "Am I a morning person?",
     "gold_keys": ["wake_up_time", "morning_routine"], "query_type": "semantic",
     "notes": "No — three alarms, rushed, skip breakfast"},

    {"id": 12, "question": "Which professor pushes me the hardest academically?",
     "gold_keys": ["prof_ayesha", "prof_imran"], "query_type": "semantic",
     "notes": "Mam Ayesha strictest; Sir Imran most demanding"},

    {"id": 13, "question": "Am I financially comfortable as a student?",
     "gold_keys": ["allowance", "expenses"], "query_type": "semantic",
     "notes": "No — only 2-3k left by end of month"},

    {"id": 14, "question": "How do I cope with having too many assignments at once?",
     "gold_keys": ["assignment_load", "health_sleep"], "query_type": "semantic",
     "notes": "Sleep deprivation + tea to keep going"},

    {"id": 15, "question": "How do I get to university when I miss the morning bus?",
     "gold_keys": ["rickshaw", "bus_timing"], "query_type": "semantic",
     "notes": "Rickshaw 150 rupees, 20 minutes"},

    {"id": 16, "question": "What subject have I struggled with the most at university?",
     "gold_keys": ["worst_grade", "class_linear_algebra"], "query_type": "semantic",
     "notes": "Linear Algebra — got a C, underestimated derivation practice needed"},

    {"id": 17, "question": "How active is my social and extracurricular life?",
     "gold_keys": ["study_group", "sport_team"], "query_type": "semantic",
     "notes": "Study group + cricket team on weekends"},

    {"id": 18, "question": "What is causing me the most academic stress right now?",
     "gold_keys": ["exam_ds_date", "assignment_load"], "query_type": "semantic",
     "notes": "Midterm Thursday + 3 assignments due simultaneously"},

    {"id": 19, "question": "How do I spend my free time when there are no assignments?",
     "gold_keys": ["sport_cricket", "hobby_gaming", "hobby_reading"],
     "query_type": "semantic",
     "notes": "Cricket Saturday, Valorant with Hassan, Atomic Habits before bed"},

    {"id": 20, "question": "What are my sleeping and eating habits like?",
     "gold_keys": ["health_sleep", "food_habits"], "query_type": "semantic",
     "notes": "5-6h sleep, skip breakfast, heavy lunch, canteen samosa"},

    # ── Multi-hop (10) ────────────────────────────────────────────────────────
    {"id": 21, "question": "What hostel do I live in and which floor is my room on?",
     "gold_keys": ["hostel_name", "hostel_room"], "query_type": "multi_hop",
     "notes": "Iqbal Hostel + 2nd floor room 215 — needs both memories"},

    {"id": 22, "question": "Who do I study with for exams and where do we sit?",
     "gold_keys": ["study_group", "library_spot"], "query_type": "multi_hop",
     "notes": "Omar + Zara + corner table 2nd floor library"},

    {"id": 23, "question": "Which subject gave me my worst grade and who teaches it?",
     "gold_keys": ["worst_grade", "prof_saba"], "query_type": "multi_hop",
     "notes": "Linear Algebra (C) + Mam Saba teaches it"},

    {"id": 24, "question": "When is my upcoming midterm and what topics will it cover?",
     "gold_keys": ["exam_ds_date", "exam_ds_topics"], "query_type": "multi_hop",
     "notes": "Thursday 9 AM + binary trees / heaps / BFS / DFS"},

    {"id": 25, "question": "What tool does my pending assignment need and when is it due?",
     "gold_keys": ["assignment_due_net", "assignment_tools_net"],
     "query_type": "multi_hop",
     "notes": "Due Friday + Cisco Packet Tracer — one memory each"},

    {"id": 26, "question": "What sport do I play and who are my teammates?",
     "gold_keys": ["sport_cricket", "sport_team"], "query_type": "multi_hop",
     "notes": "Cricket + Omar, Hassan, Bilal EE — needs both memories"},

    {"id": 27,
     "question": "Who teaches my Wednesday afternoon class and what is their background?",
     "gold_keys": ["class_networks", "prof_hassan_net"], "query_type": "multi_hop",
     "notes": "Wednesday 2 PM Networks + Sir Hassan 8 years telecom"},

    {"id": 28,
     "question": "What is my FYP project and which dataset does it use?",
     "gold_keys": ["fyp_topic", "fyp_tools"], "query_type": "multi_hop",
     "notes": "Medical image classification + ChestX-ray14 from NIH"},

    {"id": 29,
     "question": "Who do I go out for biryani with and what is my relationship with them?",
     "gold_keys": ["food_biryani", "best_friend"], "query_type": "multi_hop",
     "notes": "Omar + he is my best friend since first year"},

    {"id": 30,
     "question": "Who is my FYP supervisor and what accuracy target have they set?",
     "gold_keys": ["fyp_progress", "prof_imran"], "query_type": "multi_hop",
     "notes": "Sir Imran + 90 percent target — one memory each"},
]


# ── Corpus memories (450) ─────────────────────────────────────────────────────
# These create realistic retrieval noise. They are NOT referenced by any QA pair.
# Mix of static (richer, more varied) and template-generated (bulk).

def _make_corpus() -> list[str]:
    mem: list[str] = []

    # ── Class experiences (60) ────────────────────────────────────────────────
    class_notes = [
        "Today in Data Structures we covered red-black trees. Sir Imran drew "
        "the colour-flip and rotation cases on the board three times before the "
        "class seemed to understand. I still need to practice the deletion cases.",

        "The Algorithms lecture today was on dynamic programming. Mam Ayesha "
        "walked through the coin-change problem and then assigned three variations "
        "as homework. I find the recursive memoization approach much more natural "
        "than the bottom-up table approach.",

        "OOP lab today was about implementing the Observer pattern. Sir Zafar "
        "had us model a stock market ticker with multiple listener classes. "
        "My implementation was clean but I forgot to handle the case where "
        "a listener deregisters itself during a notification cycle.",

        "Software Engineering lecture focused on sprint planning and user stories. "
        "We had to write acceptance criteria for a library management system. "
        "The professor kept reminding us that a good user story says what, "
        "not how, and I kept confusing the two in my first draft.",

        "The Linear Algebra tutorial today covered eigenvalues and eigenvectors. "
        "Mam Saba used a geometric interpretation on the board that finally made "
        "the concept click for me after weeks of purely algebraic manipulation.",

        "In today's Networks lab we used Wireshark to capture a real HTTP session "
        "and identify the three-way handshake in the packet trace. "
        "It was genuinely satisfying to see the theory from the textbook "
        "playing out in actual captured data.",

        "Data Structures quiz today covered hash tables and collision resolution. "
        "I answered the open addressing question correctly but mixed up the "
        "formulas for linear probing and quadratic probing in the written part.",

        "Mam Ayesha returned our last Algorithms assignment today. "
        "I got 17 out of 20, which I am satisfied with. She deducted marks "
        "for not proving the correctness of my greedy algorithm, only its "
        "time complexity.",

        "Networks class was cancelled today because Sir Hassan had a departmental "
        "meeting run long. We got the extra hour back and Omar and I used it "
        "to work on the FYP literature review section in the library.",

        "Sir Zafar introduced generics and type parameters in OOP today. "
        "The examples using typed collection classes made the concept very clear. "
        "I realised my FYP code has some places where generics would be cleaner "
        "than what I have written.",

        "The Linear Algebra Saturday class felt brutal this morning. "
        "I arrived five minutes late because I overslept and missed the early "
        "bus. Mam Saba had already started the determinant expansion proof "
        "and I had to reconstruct the first steps from the student next to me.",

        "Software Engineering today we discussed the differences between waterfall "
        "and agile approaches using case studies of real software projects that "
        "failed due to poor process decisions. The examples made the abstract "
        "methodology debate much more concrete.",

        "Algorithms class today ended early because Mam Ayesha had to leave for "
        "a faculty meeting. She gave us the remaining thirty minutes as self-study "
        "time and I used it to start the practice problems for next week.",

        "Today I had back-to-back classes from 8 AM to 2 PM with only a twenty "
        "minute gap for lunch. I ate the daal chawal standing up between CS-101 "
        "and CS-204 while scrolling through lecture slides on my phone.",

        "The OOP exam simulation Sir Zafar ran today was harder than I expected. "
        "He gave us a scenario and forty minutes to design a full class hierarchy. "
        "My design was functional but less elegant than what he showed as the "
        "model answer. I need to think more carefully about single responsibility.",

        "Networks assignment grading came back today. I scored 38 out of 40. "
        "The two marks I lost were for not documenting the OSPF convergence time "
        "in my report, which I had measured but forgotten to include in the table.",

        "Data Structures lecture was on graph algorithms today. Sir Imran did "
        "Dijkstra's shortest path with a detailed step-by-step trace on a "
        "seven-node example graph. The priority queue implementation detail "
        "is what trips most students and he emphasised it twice.",

        "In Linear Algebra today we started matrices and linear transformations. "
        "Mam Saba showed the geometric meaning of matrix multiplication as "
        "composition of transformations, which is a perspective I had never "
        "encountered before and it completely changed how I think about matrix math.",

        "I got called on in Algorithms today to explain the proof of the greedy "
        "exchange argument for the activity selection problem. I managed to get "
        "most of it right but stumbled on the base case, which Mam Ayesha "
        "corrected patiently in front of the class.",

        "Software Engineering scrum today went poorly. My team's sprint demo "
        "was not ready because one group member had not pushed their changes "
        "to the shared repository. The professor told us this is exactly the "
        "coordination problem agile is supposed to prevent.",

        "The first Data Structures assignment of the semester is out. "
        "It asks us to implement a self-balancing BST from scratch in C++. "
        "The deadline is two weeks away but I know from experience I should "
        "not wait until the last few days.",

        "Today we had a guest lecture in Software Engineering from a developer "
        "at a local tech company who talked about CI/CD pipelines in production. "
        "He showed us their actual GitHub Actions config, which was the most "
        "practically useful thing I have seen in a classroom this semester.",

        "Mam Ayesha started us on graph theory in Algorithms today. "
        "BFS and DFS both came up and she connected them directly to the "
        "Data Structures content from Sir Imran's class, which helped reinforce "
        "both subjects simultaneously.",

        "The Networks midterm from last semester was posted as practice material "
        "today. Sir Hassan said the upcoming midterm will follow a very similar "
        "format and that the subnetting questions will be at least thirty percent "
        "of the marks.",

        "OOP class today was the most interesting lecture of the semester so far. "
        "Sir Zafar walked through a refactoring of a messy codebase, applying "
        "design patterns one by one and showing how each one reduced coupling "
        "and improved testability. It was a live demonstration of clean code.",

        "Linear Algebra tutorial session today was focused entirely on practice "
        "problems for the upcoming midterm. Mam Saba solved five problems on the "
        "board and then had us attempt three more in pairs. My partner was Zara, "
        "which made the session very productive.",

        "Data Structures today covered hashing in depth including load factor, "
        "rehashing triggers, and the performance characteristics of different "
        "probing strategies. I took very detailed notes and added diagrams "
        "to my notebook.",

        "I almost fell asleep in Networks today. The 2 PM afternoon slot is "
        "brutal after a heavy cafeteria lunch. I started taking notes by hand "
        "instead of on my laptop to force my brain to stay engaged.",

        "Algorithms class today was a problem-solving session rather than a "
        "lecture. Mam Ayesha divided us into groups of three and gave each group "
        "a different NP-hard problem to present a reduction for. "
        "Our group got the subset sum problem.",

        "Software Engineering today: we had to estimate story points for a set "
        "of user stories using planning poker. It was surprisingly difficult "
        "to agree as a team and the disagreements revealed genuine differences "
        "in how we each understood the requirements.",

        "Sir Imran announced that next week's Data Structures lecture will be "
        "entirely on B-trees and their use in database indexing. "
        "He recommended reading chapter 18 of CLRS before attending so that "
        "the lecture time can focus on exercises rather than theory.",

        "Mam Saba gave us a formulas sheet today listing every property and "
        "theorem we need to know for the midterm. Having a single page reference "
        "is actually more anxiety-inducing than I expected because it makes "
        "the scope of the exam very explicit.",

        "In OOP today we discussed the trade-offs between inheritance and "
        "composition. Sir Zafar is a firm believer in composition over "
        "inheritance and he demonstrated three specific cases where inheritance "
        "created rigid and fragile class hierarchies.",

        "Algorithms midterm results came back. I got 72 out of 100, which puts "
        "me comfortably above the class average but not in the top tier. "
        "The proof I lost the most marks on was the amortised analysis question, "
        "which I had studied but not practiced enough on paper.",

        "I stayed back after Networks class today to ask Sir Hassan about a "
        "specific question on our assignment. He spent twenty minutes explaining "
        "OSPF designated router election to me one-on-one, which was more "
        "helpful than any amount of reading could have been.",

        "Data Structures extra tutorial today was about applying graph algorithms "
        "to real-world routing problems. Sir Imran brought in a simplified "
        "version of a real routing table and had us trace through the shortest "
        "path computation by hand on a projected map.",

        "The Algorithms assignment submission portal crashed thirty minutes before "
        "the deadline tonight. Half the class was trying to submit at the same time. "
        "Mam Ayesha extended the deadline by two hours via email, which I "
        "only saw after I had already panic-submitted an earlier draft.",

        "OOP lab today had us implement the full MVC pattern for a simple "
        "student grade tracker application. Getting the model, view, and "
        "controller to interact without tight coupling took longer than expected "
        "but the end result was genuinely clean code.",

        "Linear Algebra class today was cancelled without notice. "
        "I walked to the classroom and found an empty room with a note saying "
        "class was moved to next Saturday. I then went to the library instead "
        "and studied for the Data Structures midterm.",

        "Software Engineering group project presentation today. My team presented "
        "our design for a university course registration system. The professor "
        "asked hard questions about scalability and we did not have very good "
        "answers for the database design decisions.",

        "Networks class ended with Sir Hassan recommending a book called "
        "Computer Networks: A Top-Down Approach by Kurose and Ross. He said "
        "it is the clearest explanation of networking concepts he has ever "
        "read and that it complemented his lecture notes very well.",

        "I missed Data Structures today because of an appointment at the campus "
        "medical centre. I texted Omar and he sent me photos of the full whiteboard "
        "at the end of the lecture. I owe him a biryani for that.",

        "Algorithms class today used the maximum flow problem as the entry point "
        "to network flow theory. Mam Ayesha built up the Ford-Fulkerson algorithm "
        "step by step from first principles before showing the augmenting path "
        "intuition that makes it work.",

        "OOP today discussed exception handling design. Sir Zafar showed examples "
        "of poor exception handling that swallowed errors silently and good "
        "exception handling that preserved the error chain. "
        "A common mistake he sees in student code is catching Exception directly.",

        "I ran into Sir Imran in the corridor today outside of class. "
        "He asked about my FYP progress and I told him about the accuracy jump "
        "from the data augmentation experiment. He nodded and said to also "
        "try weighted loss for the minority class since pneumonia is rarer "
        "than normal cases in the training data.",

        "Linear Algebra practice session with Zara today in the library. "
        "We went through the entire eigenvalue chapter together and she caught "
        "a fundamental misunderstanding I had about how characteristic polynomials "
        "connect to the determinant. An hour with her was worth four hours alone.",

        "Networks final assignment topic was announced today: design a complete "
        "enterprise network architecture for a fictional hospital with separate "
        "segments for patient records, imaging systems, and administration. "
        "This is easily the most complex assignment of the semester.",

        "Data Structures revision session with Omar tonight in the library. "
        "We traced through deletion from AVL trees on paper for two hours. "
        "Omar found a case I had completely missed: deleting a node that causes "
        "a cascade of two rotations. We re-derived it together.",

        "Sir Zafar posted a code review rubric on the course portal today. "
        "It explicitly awards marks for naming conventions, single responsibility, "
        "and documentation quality, not just for working output. "
        "This changes how I will approach the remaining lab assignments.",

        "Today I sat in on an optional research seminar about neural architecture "
        "search, which is directly relevant to my FYP. The visiting professor "
        "talked about automating the design of convolutional network architectures, "
        "which gave me several ideas for my chest X-ray classification model.",

        "Mam Ayesha sent an email today reminding us that the Algorithms final "
        "will be entirely theoretical, no coding, and that proofs must be written "
        "in proper mathematical notation. I need to practice writing formal "
        "proofs more carefully than I have been doing in my revision sessions.",

        "Networks simulation lab today we had to observe packet loss behaviour "
        "by artificially throttling bandwidth in Packet Tracer and then analyse "
        "the TCP congestion window behaviour. The visual graph of the window "
        "size sawtoothing up and down made the theory very tangible.",

        "OOP assignment released today: implement a design pattern of our choice "
        "for a parking lot management system. I am going to use the Factory "
        "pattern for vehicle type creation and the Observer pattern for "
        "availability notifications. Sir Zafar approved my choice in office hours.",

        "Data Structures final lab exam date announced: three weeks from now "
        "in the PC lab. Sir Imran said it will involve implementing two data "
        "structures from scratch in C++ under time pressure. "
        "I need to practice implementing from memory, not just understanding the concepts.",

        "Software Engineering retrospective meeting today with my project team. "
        "We identified three main issues from the last sprint: unclear requirements, "
        "one team member doing most of the work, and no test coverage. "
        "We agreed specific action items for the next sprint.",

        "Linear Algebra end-of-chapter review today. Mam Saba went back to the "
        "beginning of the chapter and showed how every concept builds on the "
        "previous one from vectors to spaces to transformations to eigenvalues. "
        "It was a genuinely illuminating structural overview.",

        "I spent two hours in the PC lab today fixing a segmentation fault in "
        "my Data Structures assignment. The bug turned out to be a null pointer "
        "dereference in the tree deletion function, caused by not checking "
        "for an empty subtree before accessing a child node.",

        "Algorithms class today was about string matching algorithms. "
        "Mam Ayesha covered the naive O(nm) approach, then the KMP algorithm "
        "and its failure function, then introduced Rabin-Karp as an example "
        "of a hashing-based approach. Three complete algorithms in ninety minutes.",

        "OOP today we discussed the Decorator pattern and Sir Zafar used the "
        "standard IO stream wrapping example that most textbooks use, but then "
        "showed a more interesting GUI component decoration example that I "
        "found much more illuminating for understanding the pattern's motivation.",
    ]
    mem.extend(class_notes)

    # ── Hostel life (40) ──────────────────────────────────────────────────────
    hostel_memories = [
        "The hot water in the hostel showers was off again this morning for the "
        "third time this week. I had to take a cold shower at 6:50 AM before "
        "running to the bus stop. Complaining to the hostel office has produced "
        "no results so far.",

        "Hassan stayed up until 4 AM playing Valorant with his university team "
        "last night. The keyboard clicks and occasional victory shouts made "
        "sleeping in the same room very difficult. I ended up using earplugs "
        "for the first time.",

        "The hostel common room got a new television this week. Most evenings "
        "a group of us sit there after dinner and watch cricket highlights "
        "or news. It has become an unexpected social gathering point.",

        "Power went out in the hostel for two hours last night during peak "
        "study hours. I switched to my phone hotspot and continued working "
        "on a battery-powered laptop but the heat without the fan was unbearable.",

        "I reorganised my study desk this weekend. Books sorted by subject, "
        "charger cables clipped neatly, notes filed in labelled folders. "
        "It lasted approximately one assignment crisis before reverting "
        "to its previous state of controlled chaos.",

        "The hostel warden did a room inspection today without advance notice. "
        "Hassan panicked and shoved everything under his bed in thirty seconds "
        "flat. The warden noted our room as satisfactory, which felt like a "
        "generous assessment given what was under Hassan's bed.",

        "I had dinner with four other hostel residents tonight who I do not "
        "usually eat with. One is doing final year civil engineering and another "
        "is studying pharmacy. It was a good reminder that the university is "
        "bigger than just the CS department.",

        "The hostel broadband was particularly fast tonight. I downloaded two "
        "weeks of Coursera deep learning lectures for offline viewing on the "
        "train home during the upcoming mid-semester break.",

        "Hassan cooked biryani in the common room kitchen tonight using a "
        "rice cooker and some spices he had brought from Multan. "
        "Six of us ate from the same pot. It was better than the cafeteria "
        "version and cost us a total of about 200 rupees between six people.",

        "I woke up at 3 AM to the sound of rain hammering the window. "
        "The room felt cold and I spent a few minutes just listening before "
        "going back to sleep. Rainy nights in the hostel are oddly peaceful "
        "when there are no assignments due the next morning.",

        "A second year student knocked on our door tonight asking for help "
        "with his Programming Fundamentals assignment. Hassan and I spent "
        "forty minutes walking him through loops and arrays. It felt good "
        "to be on the teaching side of that conversation for once.",

        "The hostel notice board has a new poster for a university programming "
        "competition next month. Cash prizes for the top three teams. "
        "I asked Omar if he wants to enter together. He immediately said yes "
        "without asking about the prize amount, which is very Omar.",

        "I cleaned under my desk today and found three old assignment printouts "
        "from last semester, two empty water bottles, and one sock that I "
        "had been missing for over a month. The hostel room holds secrets.",

        "Someone in the room next to ours has started playing guitar in the "
        "evenings. The music carries through the thin walls. It is not "
        "technically distracting and is actually quite a pleasant background "
        "sound during light revision sessions.",

        "The hostel cafeteria introduced a new biryani dish today at 120 rupees. "
        "It is slightly overpriced by hostel standards but significantly more "
        "convenient than walking to the off-campus dhaba in the heat.",

        "I fell asleep at my desk tonight while reading the Networks textbook. "
        "I woke up an hour later with a keyboard imprint on my cheek and "
        "a cramp in my neck. Hassan took a photo before waking me, which "
        "I have already made him delete.",

        "Room inspection passed again this week. The secret is to do a "
        "five-minute sweep every Sunday regardless of how tired you are. "
        "Future me is always grateful to past me for this habit.",

        "A hostel-wide water conservation notice was posted today asking "
        "us to limit shower time to five minutes. The plumbing system is "
        "apparently under significant strain. Most residents ignored the notice. "
        "I am trying to actually follow it.",

        "Hassan and I agreed tonight to a noise curfew after midnight on "
        "weekdays. He stops gaming and I stop typing. It is a mutual compromise "
        "that should help both of us get slightly more sleep this semester.",

        "The view from my window onto the cricket ground is particularly nice "
        "in the late afternoon when the light is golden. I sometimes sit "
        "on the desk and look out for five minutes after a long study session "
        "as a mental reset between subjects.",

        "My desk lamp bulb burned out tonight during the middle of a study "
        "session. I had to relocate to the common room and study there "
        "until midnight under the harsh fluorescent lighting. "
        "I bought a replacement bulb the next morning.",

        "A first-year student asked me in the corridor today if living in "
        "Iqbal Hostel was good. I told him honestly: the location is excellent, "
        "the facilities are adequate, the social life is surprisingly good, "
        "and the wifi is functional but not fast enough for large downloads.",

        "I did laundry tonight, which I had been postponing for a week. "
        "The hostel laundry room has three machines for over a hundred "
        "residents. The trick is to go at 11 PM when most people have gone "
        "to bed and all the machines are free.",

        "Omar came over to our room to study for a few hours tonight. "
        "Hassan joined us briefly for one chapter of Linear Algebra before "
        "giving up and going back to his game. The three of us sharing "
        "one room is chaotic but somehow productive.",

        "I bought a small electric kettle for the room this week. "
        "It has completely changed my evening study routine. "
        "Instant tea on demand without going down to the canteen is "
        "a quality of life improvement I cannot believe I lived without.",

        "The hostel ground cricket match today was a proper competitive game "
        "against the management sciences hostel. We lost by eight runs "
        "in the final over. I was run out for 27, which I am still "
        "annoyed about because the call was genuinely marginal.",

        "I updated my room wall with a printed semester schedule, exam dates, "
        "and FYP milestones all on one A3 sheet. Having the full semester "
        "visible at once makes it much easier to plan backwards from deadlines.",

        "Hassan and I had our first genuine disagreement tonight about the "
        "room temperature. I prefer cooler, he prefers warmer. "
        "We compromised on 22 degrees with the fan on low, which neither "
        "of us is fully happy with but both of us can live with.",

        "The hostel mess committee met today and I attended as the CS block "
        "representative. We discussed the food quality complaints that have been "
        "coming in and agreed to propose three new menu items to the caterer. "
        "I suggested adding proper nihari on Sundays.",

        "I practiced public speaking tonight by explaining my entire FYP to "
        "Hassan as if he were a non-technical supervisor. He asked surprisingly "
        "good questions, including why we need X-rays when doctors have "
        "other tests available, which is a legitimate question I should "
        "address in my thesis introduction.",

        "Stayed up until 2 AM tonight finishing the OOP assignment and then "
        "could not sleep because my brain was still running problem-solving "
        "loops. I eventually put on a podcast about history and fell asleep "
        "about thirty minutes into an episode about the Roman Empire.",

        "A package from home arrived at the hostel reception today. "
        "My mother sent homemade achaar, some dry fruit, and a sweater "
        "for the upcoming winter months. The achaar alone is going to "
        "significantly improve the quality of the cafeteria daal.",

        "The hostel lights in the corridor have been flickering for a week. "
        "Three separate requests to the maintenance team have produced "
        "no visible action. I have started carrying a small torch in my "
        "bag as a precaution after tripping in the dark hallway last Tuesday.",

        "I met the hostel's oldest resident tonight, a sixth-year PhD student "
        "who has been living in Iqbal Hostel for four years. He gave me "
        "one piece of advice: sleep more than you think you need to in "
        "your fourth year because nothing works properly when you are tired.",

        "Hassan's gaming chair arrived today via courier. It takes up "
        "approximately twenty-five percent of our available floor space. "
        "On the positive side, he says his posture during long sessions "
        "is now significantly better, which might reduce the midnight chair "
        "squeaking that has been another source of sleep disruption.",

        "I printed my entire FYP progress report today at the library printer "
        "and reviewed it physically with a red pen. Reading on paper "
        "reveals errors and awkward sentences that I completely miss on screen. "
        "I found eleven things to fix in the introduction alone.",

        "The hostel common area was decorated for university's annual cultural "
        "festival today. Someone had strung fairy lights across the notice board "
        "area and put a playlist of Urdu songs on the shared bluetooth speaker. "
        "It made dinner feel unexpectedly festive.",

        "I called my parents tonight for the first time in two weeks. "
        "My mother asked if I was eating properly and I said yes, which is "
        "partially true. My father asked about my CGPA, which I deflected "
        "by talking about the FYP progress instead.",

        "There was a spider in the corner of our room ceiling for three days "
        "before Hassan finally removed it. His argument was that spiders eat "
        "mosquitoes and are therefore net beneficial. My argument was that "
        "I do not want a spider in my room. We reached an impasse until "
        "the spider resolved it by relocating voluntarily.",

        "Late night in the common room tonight: four of us from the CS floor "
        "debated whether machine learning will eliminate software engineering "
        "jobs in ten years. The consensus was probably not entirely but "
        "significantly, which is both reassuring and motivating.",
    ]
    mem.extend(hostel_memories)

    # ── Social and friend memories (30) ──────────────────────────────────────
    social_memories = [
        "Omar and I went to the dhaba after a particularly long Wednesday "
        "and talked about our FYP projects over biryani. He is working on a "
        "blockchain voting system and is worried about the scalability proof "
        "of concept section. I gave him some feedback and he helped me think "
        "through my model evaluation methodology.",

        "Zara helped me understand the concept of a cofactor matrix tonight "
        "by explaining it three different ways until one of them clicked. "
        "The third explanation, using the geometric volume interpretation "
        "of the determinant, was the one that finally made sense to me.",

        "Played cricket with the full team today for the first time in two "
        "weeks. Omar bowled well, Hassan kept wicket adequately, and Bilal "
        "from EE took two catches that were genuinely difficult. "
        "We won by twenty runs and went for tea afterwards.",

        "Omar is one of the most methodical problem-solvers I have encountered. "
        "When working through algorithm problems together, he writes out every "
        "assumption before starting, which I find slow but I have noticed "
        "it means he almost never makes the careless errors I frequently make.",

        "Hassan introduced me to his hometown friend today who is visiting "
        "the campus. He is studying economics at another university in the city. "
        "We had a very interesting conversation about inflation and I realised "
        "I know almost nothing about macroeconomics.",

        "Zara is applying for a research internship at a local AI lab this "
        "summer. She asked me to review her personal statement. The writing "
        "was very strong, but I suggested she add a specific example of a "
        "research problem she worked through independently.",

        "Omar and I registered for the university programming competition "
        "today as a two-person team. We have three weeks to prepare. "
        "We decided to focus on graph algorithms and dynamic programming "
        "since those tend to dominate competitive programming problem sets.",

        "Had a long phone call with my younger sister tonight. She is applying "
        "to university next year and was asking about the CS program. "
        "I told her honestly: it is hard, the workload is heavy, but the "
        "skills you build are genuinely valuable and the classmates make it "
        "worthwhile.",

        "Bilal from EE lent me his old Networks textbook today because my "
        "copy had not arrived yet from the bookshop. He said he passed the "
        "subject with it so it clearly worked. Useful friend to have "
        "across department lines.",

        "The four of us, me, Omar, Zara, and Hassan, watched a classic cricket "
        "match recording in the common room tonight instead of studying. "
        "It was a justified break after a particularly difficult midterm week "
        "and the morale boost was real.",

        "I asked Omar why he is always calm before exams. He said he studies "
        "until he genuinely cannot think of a single thing he does not know, "
        "which usually happens about two days before the exam. "
        "I am going to try adopting this approach instead of last-minute cramming.",

        "Zara mentioned today that she is considering doing a PhD after graduation. "
        "She asked my opinion and I said I thought she would be very good at it. "
        "She asked if I was considering the same and I said probably not, "
        "which surprised her given how deeply I am engaged with the FYP.",

        "Had tea with three classmates I do not usually spend time with today "
        "in the cafeteria. We talked about internship applications and "
        "which local companies have the best internship programs for CS students. "
        "The consensus was that the mid-size tech companies offer more "
        "meaningful work than the large multinationals.",

        "Hassan and I played Valorant together tonight for the first time in "
        "weeks. We won four out of six games, which is a positive trend. "
        "He grudgingly admitted that my aim has improved since I started "
        "playing seriously instead of just pressing buttons hopefully.",

        "Omar ran a mock interview session with me today, asking standard "
        "technical interview questions on data structures and algorithms. "
        "I froze on the question about detecting cycles in a graph using "
        "DFS, which is embarrassing given that we just covered it in class.",

        "Zara organised a group study session in the library for the entire "
        "Algorithms class today. About twelve people showed up, which was "
        "more than expected. She led the session systematically and it was "
        "one of the most productive study hours I have had this semester.",

        "I talked to Bilal from EE about his experience in the engineering "
        "curriculum versus mine in CS. He finds circuit analysis very abstract "
        "in the same way I find Linear Algebra abstract. "
        "We agreed that being forced through difficult mathematics is "
        "probably good for long-term problem-solving ability.",

        "Omar sent me a research paper about transformer architectures at "
        "midnight with no context. I read the abstract and fell asleep. "
        "By morning he had already read the full paper and was ready to "
        "discuss it. Different study styles, same outcome eventually.",

        "Celebrated Hassan's birthday tonight with a small group from the "
        "hostel floor. Someone ordered a cake from the campus bakery "
        "and we all chipped in. It was a genuinely warm evening and "
        "Hassan seemed genuinely surprised despite having mentioned it "
        "himself twice in the preceding week.",

        "Went to the campus book fair today with Omar and found an almost "
        "new copy of CLRS for 300 rupees. It is technically the second "
        "edition and the algorithms are in pseudocode rather than a real "
        "language, but for reference and exam preparation it is perfect.",

        "Zara sent me a very detailed feedback document on my draft FYP "
        "report introduction. She identified six places where my claims "
        "were not supported by citations, two places where the logic "
        "jumped without explanation, and one paragraph that she diplomatically "
        "described as 'needing significant revision'.",

        "Omar and I went for a walk around campus after dinner tonight. "
        "No phones, no study material. Just a forty-minute walk and a "
        "conversation about everything except university work. "
        "I feel better than I have in two weeks.",

        "Hassan asked me to teach him TensorFlow basics tonight. "
        "I spent ninety minutes explaining tensors, layers, and backpropagation "
        "at a very high level. He seemed genuinely interested and asked "
        "if he should do a machine learning minor. I said absolutely yes.",

        "Group photo with Omar, Zara, and Bilal after the cricket match today. "
        "First semester we were strangers in a queue for registration. "
        "Third year we were study partners. Fourth year we are the people "
        "who show up for each other without being asked.",

        "Zara asked me to review her CV today for internship applications. "
        "It was already very strong but I noticed she had not highlighted "
        "her class ranking prominently, which is the first thing most "
        "technical recruiters look for in fresh graduate applications.",

        "Bilal from EE told me today that EE students have a compulsory "
        "programming course in their third year and most of them find it "
        "very difficult. He said our CS curriculum does not adequately "
        "prepare us for the hardware layer, which is probably fair.",

        "Omar received a call-back for a summer internship interview today. "
        "He practised his answers with me for two hours the night before "
        "the interview. He is calm under pressure in a way that I genuinely "
        "admire and am actively trying to learn from.",

        "Hassan told me his goal after graduation is to join a gaming company "
        "as a game developer. He showed me a small game prototype he built "
        "in Unity during the last semester break. It was more technically "
        "impressive than I expected. He is clearly more skilled than his "
        "current grades suggest.",

        "I played in a cricket practice session with the hostel team tonight "
        "even though there was no match scheduled. Bilal wanted to work on "
        "his batting and asked me to bowl at him. I bowled for forty minutes "
        "straight and my shoulder is telling me I was not conditioned for that.",

        "Zara, Omar, and I had a debate today about which is harder: "
        "getting a high GPA or building impressive personal projects. "
        "Zara said GPA, Omar said projects, I said they require completely "
        "different types of effort and the question itself is not well defined.",
    ]
    mem.extend(social_memories)

    # ── Food and campus life (25) ─────────────────────────────────────────────
    food_campus = [
        "The cafeteria introduced a new menu this week. Haleem has been added "
        "on Tuesdays and Thursdays. It is 90 rupees for a bowl and significantly "
        "better than the biryani they normally serve on those days.",

        "I counted today: I have eaten daal chawal eleven times in the last "
        "two weeks. It is cheap, filling, and consistently available. "
        "It is the university cafeteria equivalent of a default setting.",

        "The dhaba outside the gate raised their biryani price from 150 to "
        "170 rupees this week. Omar was visibly bothered by this. "
        "We went anyway, because the alternative is the cafeteria biryani "
        "which is not a realistic comparison.",

        "I tried the new pasta dish at the cafeteria today. "
        "It was ambitious but not quite successful. I finished it because "
        "I was hungry, not because I enjoyed it. The daal chawal remains "
        "the only reliable option in my view.",

        "A chai cart has been parked outside the library building every "
        "evening this week. Two rupees more expensive than the canteen "
        "stall but the cups are bigger and the tea is stronger. "
        "I have become a regular customer.",

        "I bought a bag of mixed dry fruit from the campus general store "
        "to keep at my desk as a late-night snack alternative to canteen "
        "samosas. Healthier, cheaper per unit, and available without a "
        "ten-minute walk after 10 PM.",

        "There was a food stall festival on the main campus lawn today. "
        "At least twenty student organisations were selling food as "
        "fundraisers. I tried gol gappay from the chemistry society stall "
        "and a sandwich from the business school stall. "
        "The gol gappay were significantly better.",

        "The university health centre sent an email today reminding students "
        "to maintain a balanced diet. I read it while eating a samosa. "
        "I am aware of the irony.",

        "Omar and I discovered a new place near the back gate today. "
        "They serve karahi and fresh naan for 200 rupees per person, "
        "which is expensive by our standards but completely worth it "
        "as an occasional meal rather than a daily option.",

        "The canteen stall near the engineering block sells better chai "
        "than the main cafeteria. It takes an extra five minute walk "
        "but the quality difference is significant enough to justify "
        "the time on days when I need a mental pick-up between lectures.",

        "University library has a small coffee machine on the ground floor "
        "that was installed this semester. It is 30 rupees per cup and the "
        "coffee is mediocre but having caffeine available without leaving "
        "the building during exam week is very convenient.",

        "Cafeteria was closed today for a maintenance shutdown. "
        "Most of the campus descended on the dhaba outside the gate "
        "simultaneously. The wait time was forty-five minutes. "
        "I eventually got the biryani and it was worth the wait.",

        "I started tracking what I eat each day in a small notebook this week "
        "as a health experiment. After four days the dominant pattern is "
        "daal chawal for lunch, samosa in the afternoon, and some form of "
        "rice-based dish for dinner. The variety is not inspiring.",

        "The campus bakery near the main gate sells fresh buns every morning "
        "from 7 AM. On the rare occasions I have time before the bus, "
        "I buy two for 30 rupees and eat them on the shuttle. "
        "This is the best version of my morning routine.",

        "A senior student told me today that the dhaba biryani quality "
        "was dramatically better two years ago before the owner changed "
        "suppliers. Current me cannot evaluate this claim but present-day "
        "biryani is still the best available in the area by my reckoning.",

        "Tried the campus cricket ground tea stall today after the match. "
        "The tea there is served in clay cups, which is an aesthetic choice "
        "that genuinely improves the experience. Also 20 rupees, which is "
        "the cheapest tea available anywhere near the university.",

        "The cafeteria now has a digital display showing today's menu outside "
        "the entrance. This is a genuine quality of life improvement. "
        "Previously you had to walk all the way to the serving counter "
        "before discovering that the biryani was finished.",

        "I made a deal with myself this week: if I hit my FYP training "
        "milestone by Thursday, I will treat myself to the restaurant "
        "near the university that Omar has been recommending. "
        "It costs 400 rupees per person which is a special occasion price.",

        "The canteen samosas are smallest on Mondays and Fridays for reasons "
        "no one can explain. This is an empirical observation made over "
        "two semesters and I consider it a reliable data point.",

        "Campus kiosk near the CS building started stocking Red Bull this week. "
        "It costs 120 rupees, which is significantly above what I am willing "
        "to spend on a beverage, but I understand the market they are targeting "
        "given the density of sleepless final year students nearby.",

        "Omar believes that the optimal cafeteria strategy is to arrive at "
        "exactly 1:10 PM, which is after the first lunch rush but before "
        "the food starts to run out. I have validated this theory over "
        "several weeks and he is correct.",

        "Had my first proper home-cooked meal in six weeks when I went home "
        "for the mid-semester break. My mother made daal makhni, chicken "
        "karahi, and fresh roti. It was the best meal I had eaten in months "
        "and reminded me that cafeteria food is a deeply compromised version "
        "of real food.",

        "The library vending machine has been stocked with instant noodles "
        "for the first time. This is clearly targeted at exam period students "
        "who camp in the library overnight. The price is 80 rupees which "
        "is fair given the captive audience.",

        "A group of us from the hostel cooked together in the common room "
        "kitchen tonight. Hassan made rice, I made a basic dal, someone else "
        "contributed leftover chicken from the cafeteria. "
        "Eating together at a long table was more enjoyable than eating alone "
        "at the cafeteria, regardless of food quality.",

        "Campus food truck festival today in the parking lot behind the admin "
        "building. I spent 350 rupees across four different stalls. "
        "That is more than my usual daily food budget but the experience "
        "of eating outdoors in pleasant weather with a crowd of students "
        "was worth it as an occasional event.",
    ]
    mem.extend(food_campus)

    # ── Personal reflection and health (20) ───────────────────────────────────
    reflection_health = [
        "I spent some time tonight thinking about what I actually want to do "
        "after graduation. The clearest answer I can give is that I want to work "
        "on AI systems that have genuine real-world impact, not just technically "
        "impressive demos. The FYP has made that preference very concrete for me.",

        "I am genuinely struggling with time management this semester. "
        "There are more high-priority tasks than hours available and something "
        "always slips. I am trying to address this by blocking specific two-hour "
        "windows for each subject in my daily schedule rather than working "
        "reactively on whatever feels most urgent.",

        "Went for a twenty minute walk around the campus perimeter tonight "
        "with no phone or music. Just thinking. I have been spending so much "
        "time in front of screens that I had forgotten what it feels like "
        "to just observe surroundings without a task attached to them.",

        "I have been drinking too much tea. My current rate is between three "
        "and five cups a day. The afternoon cup is necessary but the midnight "
        "cup is probably counterproductive given that it delays sleep. "
        "I am going to try replacing the last cup with warm water.",

        "Got my blood pressure checked at the campus clinic today as part of "
        "a health awareness campaign. It was normal, which surprised me given "
        "the stress levels this semester. Apparently five to six hours of sleep "
        "and substantial daily walking keeps some things in check.",

        "I have been avoiding calling home as often as I should because "
        "my parents always ask how I am doing and the honest answer would "
        "take longer to explain than I have the energy for most evenings. "
        "I need to make more time for those calls.",

        "Starting to feel the accumulation of a long semester. I am not burned "
        "out exactly but I am noticeably less curious and creative than I was "
        "in September. I am hoping the mid-semester break restores some of that "
        "baseline intellectual energy.",

        "I made a decision today to stop looking at my phone for the first "
        "thirty minutes after waking up. Two days in and it is harder than "
        "expected. The impulse to check notifications the moment I open my "
        "eyes is apparently quite deeply installed.",

        "Tried meditation tonight for the first time, using a guided session "
        "I found on YouTube. Ten minutes of focused breathing. "
        "I fell asleep at minute seven, which either means it worked "
        "or I was more tired than I thought.",

        "I had a headache for most of today that I could not shake. "
        "Probably a combination of inadequate sleep, too much screen time, "
        "and not enough water. I drank two litres of water in the evening "
        "and the headache resolved by 9 PM.",

        "The mid-semester break starts next Friday. I am planning to go home "
        "for the full week. I have enough FYP experiments queued up on Colab "
        "that the training can run unsupervised while I am away and I can "
        "review the results when I get back.",

        "I realised today that I have not done any exercise beyond walking "
        "since the cricket season started three months ago. My back has been "
        "protesting the long hours at the desk. I am going to start doing "
        "basic stretches in the room morning and evening.",

        "Had a productive conversation with my academic advisor today. "
        "She reviewed my transcript and confirmed that my CGPA is on track "
        "for a reasonable graduate school application, provided my final "
        "year results maintain or improve my current average.",

        "I have started keeping a short daily log in a small notebook, "
        "just three to five sentences about what I did and how I felt. "
        "It takes five minutes before sleeping and is already helping me "
        "notice patterns in my productivity and energy levels.",

        "The stress of this semester is different from previous ones. "
        "Before, the stress was mostly about passing. Now it is about doing "
        "good enough work to be genuinely proud of and to build things that "
        "matter. That is a better kind of pressure but it is still pressure.",

        "I bought a blue light blocking glasses pair from the campus stall "
        "this week. The vendor claimed they would reduce eye strain from "
        "screens. After a week of consistent use I am not sure if they "
        "work or if I just notice my eye strain less because I expect to. "
        "Placebo or not, I will keep wearing them.",

        "Noticed that I am most productive between 8 PM and midnight. "
        "My mornings are functional but my best thinking, deepest concentration, "
        "and most creative problem solving all happen late at night. "
        "This explains a lot about my sleep schedule and probably does not "
        "bode well for any future career with standard office hours.",

        "I talked to Sir Imran today about feeling overwhelmed with the FYP "
        "timeline. He listened, then said something useful: the goal is not "
        "to finish everything, it is to finish the right things. "
        "He told me to write a priority list and cross off the bottom half "
        "immediately. I did. It genuinely helped.",

        "The campus counselling service is offering stress management workshops "
        "every Wednesday. I signed up for the next one mostly out of curiosity. "
        "Several of my classmates have attended and reported it being more "
        "practically useful than they expected from a university service.",

        "I spent the afternoon in the campus garden reading a paper for my "
        "FYP literature review. Sitting outside in the sun with a physical "
        "printout instead of a screen was productive in a different way. "
        "I made better notes and retained more than I do in the library.",
    ]
    mem.extend(reflection_health)

    # ── FYP and tech (25) ─────────────────────────────────────────────────────
    fyp_tech = [
        "Ran a new experiment on Colab today testing a ResNet-50 backbone "
        "instead of the VGG-16 I have been using. The ResNet converged faster "
        "and generalised slightly better, reaching 88.1 percent validation "
        "accuracy versus 87 percent for VGG-16 in the same number of epochs.",

        "Debugging the data loading pipeline today took two hours. "
        "The issue turned out to be that some images in the ChestX-ray14 "
        "dataset have four channels instead of three, causing a tensor shape "
        "mismatch deep in the model. Fixed by forcing conversion to RGB on load.",

        "Read the original ResNet paper today as part of my FYP literature "
        "review. The key insight about skip connections solving the vanishing "
        "gradient problem is described more clearly in the original paper "
        "than in any textbook summary I had read previously.",

        "Sir Imran reviewed my FYP proposal document today and returned it "
        "with comments in red pen. Most feedback was about the scope of the "
        "problem statement, which he said was too broad. I need to narrow "
        "it specifically to pneumonia detection rather than general pathology.",

        "I presented my current FYP results to a small group of classmates "
        "doing FYPs in the same research area. The feedback was mostly "
        "positive but one person pointed out that I had not compared my model "
        "against the dataset's baseline accuracy, which is an obvious gap "
        "I need to address.",

        "Implemented the weighted cross-entropy loss function today to handle "
        "the class imbalance in ChestX-ray14 where normal cases outnumber "
        "pneumonia cases significantly. The validation recall for the "
        "pneumonia class improved by six percentage points with this change.",

        "GitHub is an essential part of my FYP workflow. "
        "I commit every significant change with a descriptive message "
        "so I can roll back if an experiment goes wrong. "
        "This saved me once already when a hyperparameter change "
        "caused catastrophic performance regression.",

        "Read a survey paper today on medical image analysis with deep learning. "
        "It covered thirty-seven different studies across six disease categories. "
        "My FYP approach aligns most closely with the methods in section four "
        "on thoracic pathology detection.",

        "The Colab session disconnected tonight in the middle of a three-hour "
        "training run, losing all progress. This is the third time this has "
        "happened. I have started saving model checkpoints every ten epochs "
        "to minimise the loss when the runtime disconnects unexpectedly.",

        "Wrote the background section of my FYP report today. "
        "Covering convolutional neural networks, transfer learning, "
        "and medical image classification took four pages and eight citations. "
        "Sir Imran wants at least twenty references in the final report "
        "and I currently have twelve.",

        "My model architecture today is: ResNet-50 pre-trained on ImageNet, "
        "with the final fully connected layers replaced by two custom layers "
        "and a sigmoid output for binary classification. Training on the top "
        "two ResNet blocks plus the custom head gave the best results.",

        "I spent an hour debugging a PyTorch versus TensorFlow naming difference "
        "today. A forum post I was following used PyTorch and I was implementing "
        "in TensorFlow. The lesson is to always check the framework of code "
        "examples before spending time adapting them.",

        "Set up a systematic experiment tracking spreadsheet for the FYP today. "
        "Each row is one training run with columns for: model architecture, "
        "learning rate, batch size, augmentations, epochs, validation accuracy, "
        "precision, recall, and F1 score. It is already revealing patterns "
        "I could not see when results were scattered across different notebooks.",

        "Attended the first FYP group presentation session today. "
        "Twelve students presented five-minute progress summaries to the panel "
        "of supervising professors. I was the third presenter and felt the "
        "presentation went well. Sir Imran asked one hard question about my "
        "evaluation metric choice that I answered adequately but not brilliantly.",

        "I need to learn about explainability techniques for my FYP. "
        "Sir Imran suggested I implement Grad-CAM to visualise which regions "
        "of the X-ray the model is focusing on. This would make the results "
        "much more interpretable to a clinical audience.",

        "The difference between training accuracy and validation accuracy "
        "is my ongoing challenge. Currently they are about five percentage "
        "points apart, suggesting some overfitting. Data augmentation has "
        "helped narrow the gap but has not eliminated it.",

        "I submitted my FYP mid-year progress report today, two days before "
        "the deadline. It covers the literature review, proposed methodology, "
        "dataset description, and preliminary results. Sir Imran acknowledged "
        "receipt and said he would have feedback within a week.",

        "Implementing the Grad-CAM visualisation today. "
        "The first results are very promising. The model correctly highlights "
        "the lung regions and shows higher activation in areas that a "
        "radiologist would examine for pneumonia indicators. "
        "Sir Imran will be pleased with this addition to the demo.",

        "Had a two-hour meeting with Sir Imran today, the longest FYP "
        "consultation I have had yet. We reviewed every experiment I have run, "
        "discussed what worked and what did not, and set specific targets "
        "for the next four weeks. The meeting was intensive but left me "
        "with a very clear action plan.",

        "I am considering writing a short paper on my FYP results to submit "
        "to a student research conference. Sir Imran supports the idea and "
        "said if I can achieve 90 percent accuracy, the results would be "
        "competitive with published approaches on the same dataset.",

        "Python virtual environments and dependency management have become "
        "a significant overhead in the FYP. I have three different environments "
        "for different experiments because package version conflicts between "
        "TensorFlow, OpenCV, and some visualisation libraries are frequent.",

        "The FYP documentation requirement includes not just the written report "
        "but also a GitHub repository with a clean README, installation "
        "instructions, and a documented experiment log. "
        "I need to spend time this week making the repository presentable.",

        "Ran the model on a test set of X-ray images from a different source "
        "today, not from the ChestX-ray14 dataset it was trained on. "
        "The accuracy dropped to 79 percent, which tells me the model "
        "has learnt some dataset-specific biases and may not generalise "
        "perfectly to images from different clinical equipment.",

        "I found a pre-processing error in my data pipeline today that had "
        "been affecting all my recent experiments. I had been normalising "
        "with ImageNet mean and standard deviation, but chest X-rays have "
        "a very different intensity distribution. Correcting this improved "
        "validation accuracy by 1.8 percentage points across all architectures.",

        "Sir Imran asked me to prepare a comparative table of my model "
        "against three published baselines on the ChestX-ray14 dataset. "
        "Two of the baselines are from 2019 and my model already exceeds them. "
        "The third is a 2022 model that I am still behind but closing the gap on.",
    ]
    mem.extend(fyp_tech)

    # ── Template-generated bulk corpus (to fill remaining slots) ─────────────
    subjects = ["Data Structures", "Algorithms", "Computer Networks",
                "Linear Algebra", "OOP", "Software Engineering"]
    profs = ["Sir Imran", "Mam Ayesha", "Sir Hassan", "Mam Saba", "Sir Zafar"]
    times = ["8 AM", "9 AM", "10 AM", "11 AM", "12 PM", "2 PM", "3 PM"]
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    topics = [
        "recursion", "sorting algorithms", "binary search trees",
        "graph traversal", "dynamic programming", "divide and conquer",
        "network protocols", "TCP and UDP", "IP addressing",
        "matrix operations", "vector spaces", "linear transformations",
        "inheritance", "polymorphism", "encapsulation",
        "agile methodology", "design patterns", "unit testing",
        "hash tables", "heaps and priority queues", "minimum spanning trees",
    ]
    feelings = ["productive", "tired but focused", "behind schedule",
                "more confident", "slightly overwhelmed", "pleasantly surprised"]
    locations = ["the library", "the CS lab", "the cafeteria",
                 "the hostel common room", "the study room", "the corridor"]

    generated: list[str] = []
    for i, topic in enumerate(topics):
        subj = subjects[i % len(subjects)]
        prof = profs[i % len(profs)]
        t = times[i % len(times)]
        d = days[i % len(days)]
        f = feelings[i % len(feelings)]
        loc = locations[i % len(locations)]

        generated += [
            f"Today's {subj} class at {t} on {d} covered {topic} in depth. "
            f"I left the lecture feeling {f} about the material.",

            f"{prof} explained {topic} today using a worked example that finally "
            f"made the concept click. I went back to {loc} afterwards to "
            f"practice the same type of problem on my own.",

            f"Studied {topic} for two hours in {loc} tonight. "
            f"I used the technique of teaching it back to Omar to check "
            f"whether I had actually understood it or just read it.",

            f"Quiz on {topic} returned today. My score was satisfactory "
            f"but I lost marks on the edge case question, which is a pattern "
            f"I need to address in how I approach revision.",

            f"Assignment on {topic} submitted tonight just before the deadline. "
            f"I spent the last hour fixing a logic error that I had introduced "
            f"while rushing. The final solution was clean but the process was stressful.",

            f"Revised {topic} from scratch tonight using lecture notes and "
            f"the textbook together. Writing a one-page summary in my own words "
            f"is the best study technique I have found for this subject.",

            f"{subj} tutorial today in {loc} focused entirely on {topic}. "
            f"The TA walked through three examples and then gave us five problems "
            f"to attempt independently. I completed four out of five correctly.",

            f"I could not follow the {topic} section of today's {subj} lecture "
            f"because I had not reviewed the prerequisite material from last week. "
            f"I am going back to fill that gap before the next class.",

            f"Past paper practice on {topic} tonight revealed that I understand "
            f"the concept conceptually but am slow at applying it under exam time "
            f"pressure. I need timed practice sessions, not just reading.",

            f"Discussed {topic} with Zara today and she explained it from "
            f"a completely different angle than the professor had used. "
            f"Her explanation was more intuitive for how my brain works.",
        ]

    # Generate transport, routine, and miscellaneous variety
    misc_templates = [
        "The 7:30 AM bus was delayed by ten minutes today because of road "
        "works near the main gate. Several students who would normally have "
        "been late were actually on time for once.",

        "I walked to campus today instead of taking the bus because the weather "
        "was unusually mild. The twenty-five minute walk was a good way to "
        "review lecture notes out loud to myself without disturbing anyone.",

        "Rickshaw drivers near the hostel have started recognising me. "
        "One of the regulars now asks me about my exams whenever I take his "
        "rickshaw, which is both charming and mildly pressure-inducing.",

        "The campus parking lot was completely full today because of a "
        "university open day event for prospective students. "
        "Extra shuttle buses were running and the journey took twice as long.",

        "I reviewed my study schedule tonight and realised I had allocated "
        "too little time for Linear Algebra relative to how difficult I "
        "find the subject. I am rebalancing from tomorrow.",

        "Attended the CS department seminar today on industry trends. "
        "A visiting speaker from a local AI startup talked about their use "
        "of machine learning for financial fraud detection. "
        "The practical deployment challenges they described were very different "
        "from what we learn in theoretical ML courses.",

        "Library books I reserved two weeks ago finally became available today. "
        "I picked up three textbooks I need for the FYP literature review "
        "and can keep them for two weeks before renewal.",

        "Power was out in the CS building today from 10 AM to noon "
        "due to a scheduled maintenance shutdown that had not been communicated "
        "to students. The OOP lab session was cancelled and moved to next week.",

        "I used the university printing facility today to print eighty pages "
        "of research papers for the FYP. At 5 rupees a page that was 400 rupees "
        "but having physical copies to annotate is worth the cost.",

        "The weather has been significantly cooler this week, which is making "
        "the early morning 8 AM class slightly more bearable. "
        "I am waking up one alarm earlier than I was last month.",

        "University internet was extremely slow today, which disrupted my "
        "Colab session significantly. I ended up switching to my phone hotspot "
        "to push the training run through, which cost me a significant "
        "chunk of my monthly mobile data allocation.",

        "I attended the university career fair today. Several software "
        "companies had booths and I submitted my CV to three of them for "
        "their upcoming internship programs. The competition at these "
        "events is intense but it is worth showing up and making contacts.",

        "Semester fees for next term are due in three weeks. "
        "I sent my parents the fee challan amount today and they confirmed "
        "they can cover it. The tuition increase this year is significant "
        "and I know it is a genuine strain on the household budget.",

        "Had to resubmit an assignment today after discovering a fundamental "
        "error in my solution twelve hours after the deadline. "
        "The professor accepted the resubmission with a ten percent late penalty, "
        "which is fair. I learned to review my work more carefully.",

        "Campus WiFi password was changed today without announcement. "
        "The new password was eventually posted on the department notice board "
        "at 11 AM after two hours of everyone being disconnected. "
        "Not an ideal start to a day with multiple online submission deadlines.",
    ]
    generated.extend(misc_templates)

    # Pad to reach ~450 corpus memories total
    mem.extend(generated)

    # Trim or verify count
    # Static so far: 60 + 40 + 30 + 25 + 20 + 25 = 200
    # Generated: 21 topics × 10 + 15 misc = 210 + 15 = 225
    # Total: ~425 — add a few more to round to 450
    extra = [
        "I submitted my FYP bi-weekly report today and immediately started "
        "preparing for the next milestone by listing the three experiments "
        "I need to run before the following meeting with Sir Imran.",

        "The canteen stall near the library ran out of samosas by 3 PM today. "
        "This is the third time this week. Demand clearly exceeds supply "
        "at peak afternoon hours and no one has adjusted the supply accordingly.",

        "Cleaned my laptop fan today because the computer was running noticeably "
        "hot during training runs. After cleaning, the temperature during "
        "model inference dropped by six degrees and the fan noise reduced "
        "to a level that no longer disturbs Hassan during his gaming sessions.",

        "Omar sent me a link to a machine learning podcast today. "
        "I listened to one episode about transfer learning during my rickshaw "
        "ride to campus and it covered several concepts directly relevant "
        "to my FYP that I had understood theoretically but not in full depth.",

        "I updated my LinkedIn profile today for the first time in a year. "
        "Added the FYP project with a brief description and listed the "
        "technologies I have learned this semester. "
        "It feels premature to advertise skills I am still developing "
        "but the advice is to start building the profile early.",

        "The department announced a new elective on cloud computing available "
        "next semester. I am considering taking it because the skills are "
        "directly applicable to deploying the FYP model as a web service "
        "after the academic submission.",

        "Had a detailed conversation with Zara tonight about the ethics of "
        "AI in medical diagnosis. She raised the point that if my model "
        "is wrong, a real patient could be harmed. "
        "This is a responsibility I think about and it is part of why "
        "I am pushing for the highest accuracy I can achieve.",

        "I found an open-source implementation of a similar chest X-ray "
        "classifier on GitHub today. Rather than copying it, I am using it "
        "as a reference to check if my architecture and training approach "
        "are reasonable and to identify anything I might have missed.",

        "The university announced a research day next month where final year "
        "students present their projects to faculty and visiting industry guests. "
        "Sir Imran nominated my FYP as one of the presentations, "
        "which is both an honour and a motivating deadline.",

        "Went to the campus post office today to receive a courier that "
        "required physical collection. While waiting I ran into a professor "
        "from a different department who asked about my FYP when she saw "
        "the Keras logo on my laptop sticker. We had a fifteen-minute "
        "conversation about medical AI that left me with two new paper "
        "references to read.",

        "I realised today that I have been working on the FYP for over "
        "eight months already. Looking back at my first notebook entry from "
        "the beginning of the project and comparing it to where I am now "
        "is genuinely encouraging. The technical progress is measurable "
        "and the understanding has deepened significantly.",

        "Hassan showed me a short documentary about competitive gaming tonight. "
        "It made me think about passion and professionalism in a way that "
        "connected back to my own FYP work. Both require sustained deliberate "
        "practice well beyond what is comfortable or convenient.",

        "I spoke to an alumnus of the CS program today at a department event. "
        "He graduated three years ago and is now working at a tech company "
        "in Karachi. He said the one thing he wished he had done more of "
        "as a student was build real projects with real users, not just "
        "academic assignments and FYPs that only professors evaluate.",

        "Completed a full run-through of my FYP demo today, simulating "
        "the exact presentation flow I would use in front of Sir Imran "
        "and the evaluation panel. The demo takes about twelve minutes "
        "and I identified three places where the explanation was not "
        "clear enough for a non-technical audience member.",

        "Attended a workshop on academic writing today run by the department's "
        "research coordinator. The session focused specifically on writing "
        "the results and discussion section of a technical report, "
        "which is the section I am currently struggling with most in "
        "my FYP written report.",

        "Got feedback on my Networks presentation from Sir Hassan in office "
        "hours today. He said the content was technically accurate but the "
        "delivery was too fast and I needed to slow down for the diagram "
        "explanation sections. Noted.",

        "Revised my entire experiment results section tonight and added "
        "confidence intervals to all my reported metrics. "
        "Sir Imran had mentioned at the last meeting that results without "
        "uncertainty estimates are incomplete, and he was right.",

        "Bought a new notebook for FYP work today, specifically a dot-grid "
        "notebook which is better for drawing architecture diagrams than "
        "lined pages. Small tools that match the task actually do make "
        "a difference to how I work.",

        "The university library issued me a final notice today about an "
        "overdue book. It had been on my desk for three weeks instead of "
        "returned because I kept thinking I would need it again. "
        "Returned it today with the fine paid.",

        "I wrote the abstract for my FYP report tonight, which required me "
        "to summarise the entire project in 250 words. "
        "Writing an abstract is surprisingly difficult because it forces "
        "you to identify what is actually important versus what is just "
        "detailed and interesting.",

        "The CS department WhatsApp group was extremely active tonight "
        "because of a confusing announcement about final year viva dates. "
        "After forty-five minutes of contradictory messages, the department "
        "secretary posted a clear schedule that resolved the confusion.",

        "I have started using Notion to organise my FYP tasks, literature "
        "notes, and experiment results. It is significantly better than "
        "the scattered Google Docs and WhatsApp notes I was using before. "
        "The timeline view is particularly useful for FYP planning.",

        "Sir Imran told me today that a related FYP from last year's batch "
        "had been accepted to a workshop paper track. He mentioned it as "
        "a possibility for my work too if the final accuracy results "
        "are competitive with published baselines. This is now a goal.",

        "I revised the methodology section of my report for the third time "
        "today. Each revision has made it clearer and more precise. "
        "The original version was written quickly and it showed. "
        "Good academic writing requires multiple rounds of deliberate editing.",

        "Completed reading three full research papers today as part of the "
        "FYP literature review. My approach is to read the abstract and "
        "conclusion first, then the results, then the full methodology "
        "if the results are relevant. This is faster than linear reading "
        "and filters out irrelevant papers more efficiently.",
    ]
    mem.extend(extra)

    return mem


CORPUS_MEMORIES: list[str] = _make_corpus()
