# EYKO-101 sources log: minutes of video people record per day, and response-time research

Every source looked at for EYKO-101 on 21 November 2026, what it says, and how far it was checked. Searched with the web
search tool; pages opened with the fetch tool where it was allowed.

**How far each source was checked** (the citation rule: open the source and check it says what we claim):
- **Opened**: the document itself was read (quote copied from it).
- **Search text**: the quote comes from the search tool's text about that page; the page itself could not be opened
  (the fetch tool refused the domain: "Unable to verify if domain … is safe to fetch", 21 Nov). Treat as weaker.

## Used in the scenarios

| # | Source | What it says (quote) | Checked | Used for |
|---|---|---|---|---|
| S1 | Grauman et al., "Ego4D: Around the World in 3,000 Hours of Egocentric Video", CVPR 2022. https://www.cs.utexas.edu/~grauman/papers/ego4d-cvpr2022.pdf | "3,670 hours of video collected by 931 unique participants"; "Each team recruited participants to wear a camera for 1 to 10 hours at a time" | **Opened** (PDF, text extracted with pdftotext) | First-person recording happens in sessions of hours; 3,670 h / 931 wearers = 3.9 h per wearer in total (not per day) |
| S2 | "Enhancing User Navigation in Smartphone Video Playback: A Novel Method and User Interface Design", International Journal of Human–Computer Interaction, 2026. https://doi.org/10.1080/10447318.2026.2657560 | "The average length of each video was 47 s"; "The overall average was 28 videos per month"; 37.5 % recorded 10–15 videos, 42.5 % 20–30, 20 % more than 40 | Search text | **Light** scenario: 28 × 47 s a month = 0.72 min a day. Small sample: one version of the page says 40 participants (21 men, 19 women, 22–55), another 32 (24–52); how videos were counted (survey or phone log) not seen |
| S3 | Fisher et al., "Exploring the Potential of a Wearable Camera to Examine the Early Obesogenic Home Environment: Comparison of SenseCam Images to the Home Environment Interview", JMIR 2017. https://www.jmir.org/2017/10/e332 (also PMC5658644) | camera worn "during waking hours while at home for 4 consecutive days"; average wear about 5.9 h a day (SD 2.6); 15 caregivers | Search text | **Typical**: one of three measured daily wear times |
| S4 | Dementia family caregiver wearable-camera usability studies, PMC4545579 and PMC4814293 | "an average of 3.25 hours per day (range: 5.5 minutes to 9.38 hours)"; the second: "an average of 2.8 hours per day" | Search text | **Typical**: two of three measured daily wear times. Median of 2.8, 3.25, 5.9 = **3.25 h a day** |
| S5 | Gurrin et al., "Experiments in lifelog organisation and retrieval at NTCIR", 2021 chapter. https://eprints.whiterose.ac.uk/id/eprint/165106/1/Gurrin2021_Chapter_ExperimentsInLifelogOrganisati.pdf; NTCIR-14 Lifelog-3 overview https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings14/pdf/ntcir/01-NTCIR14-OV-LIFELOG-GurrinC.pdf | camera "operated for 12–14h per day (1,250–4,500 images per day—depending on capture frequency, camera type, or length of waking day)"; worn "from breakfast to sleep" at "about two images per minute" | Search text | **Heavy**: 12 h a day (lower end of 12–14) |
| S6 | Pew Research Center, "A 'Week in the Life' Analysis of Smartphone Users", 2015. https://www.pewresearch.org/internet/2015/04/01/chapter-three-a-week-in-the-life-analysis-of-smartphone-users/ | "60% of smartphone owners used their phones for taking pictures or video at least once over the course of the study period"; based on "1,035 participants who completed 10 or more surveys" | Search text | Context for light users: 40 % took no picture or video in a week; gives no minutes |
| S7 | Nielsen, "Response Times: The 3 Important Limits", NN/g (1993, updated). https://www.nngroup.com/articles/response-times-3-important-limits/ | 0.1 s feels instantaneous; 1.0 s keeps the flow of thought; 10 s keeps attention on the task | Search text | Step 5, context only |
| S8 | web.dev, "Measure performance with the RAIL model". https://web.dev/articles/rail | respond to input within 100 ms (process in 50 ms); 100–1000 ms feels like a natural progression; past 1000 ms users lose focus; past 10 s they are frustrated; the page says Core Web Vitals is now recommended over RAIL | Search text | Step 5, context only |

## Looked at, not used

| Source | Why not used |
|---|---|
| Mobile video **watching** statistics (dentsu-ho.com log study; yansmedia, demandsage, elitecontentmarketer blogs: 30 min to 1 h 19 min a day) | They measure watching, not recording. Marketing blogs without a named method |
| Sellen et al., Microsoft Research TR-2004-127, "How and Why People Use Camera Phones" (about 3 videos a month) | 2004 phones; video was a side feature then. Page not opened (domain refused) |
| photutorial.com, passport-photo.online, deseret.com, power959.com (photos and videos stored on phones) | Blogs citing other blogs; counts of stored files, not minutes recorded |
| Pew 2011–2013 "ever recorded video on a phone" (40–60 %) | Says whether people ever record, not how much |
| Autographer study "78 participants, 18–30, median 8 h a day (IQR 7–9)" | Seen only in one search summary; no paper could be found for it in a second search, so it is left out |
| Gurrin et al., AJPM 2013 ("5 hours 39 minutes" of wear) | Search text called it a smartphone study, not a camera; the page could not be opened to settle it |
| Ego4D supplement, per-site table ("262 hours … 82 participants … 3.0 hours per participant") | Site not named in the snippet; supplement PDF refused by the fetch tool |

## Searches made

1. how many minutes of video does the average smartphone user record per day statistics (extended): only viewing statistics.
2. lifelogging wearable camera study hours worn per day participants SenseCam Autographer (extended): S3, S4 leads, the Autographer claim.
3. Ego4D dataset participants hours of video recorded per participant per day collection protocol: S1.
4. camera roll study smartphone users number of videos recorded per month average video length research paper (extended): S2, TR-2004-127.
5. survey percentage of smartphone owners record video daily weekly Ofcom OR Pew (extended): S6; no Ofcom result.
6. NTCIR lifelog dataset lifelogger wearable camera images per day waking hours: S5.
7. Autographer 78 participants … median wear time 8 h: not found.
8. SenseCam "average wearing time per day was 5.9": S3 (Fisher et al.).
9. Nielsen response times; web.dev RAIL: S7, S8.
10. Domain-limited searches to get each page's own wording: tandfonline.com (S2), pewresearch.org (S6), NTCIR / whiterose / dcu (S5), nngroup.com (S7), jmir.org / PMC (S3, S4).

## Fetch attempts (21 Nov)

Two readers tried 12 pages. Refused by the fetch tool's domain check: doi.org, microsoft.com, pewresearch.org, jmir.org,
pmc.ncbi.nlm.nih.gov, research.nii.ac.jp, doras.dcu.ie, nngroup.com, web.dev, and the Ego4D supplement on cs.utexas.edu.
Only the Ego4D main paper downloaded (as a PDF); its text was extracted locally with `pdftotext`. No other download route
was used. To upgrade the "search text" rows to "opened", someone opens these pages in a browser and checks the quotes.
