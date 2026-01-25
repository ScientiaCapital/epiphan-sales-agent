# Persona-Specific Warm Script Examples

**6 Real-World Scenarios for Team Review**

These examples show how the new persona + trigger system works. Each example shows:
1. The lead's trigger action (what they did)
2. Who they are (persona)
3. The exact script the BDR receives

---

## Example 1: AV Director Downloads NC State Case Study

**Scenario**: John Smith, AV Director at University of Michigan, downloaded the NC State case study from your website.

**Trigger**: `CONTENT_DOWNLOAD`
**Persona**: `AV_DIRECTOR`

### Script Output

```
[ACKNOWLEDGE - 5 sec]
"Hi John, this is Tim from Epiphan Video. Thanks for grabbing our NC State
case study - I noticed you're at University of Michigan. Are you managing
classroom technology there?"

[CONNECT - 10 sec]
"Most AV directors who download that are dealing with the 'too many rooms,
too few people' challenge. Is remote troubleshooting something you're
dealing with?"

[QUALIFY - 10 sec]
"How many rooms are you managing, and how big is your support team?"

[PROPOSE - 5 sec]
"NC State manages 300+ rooms with a team of 3 using our fleet management
dashboard. Would a quick look at how they do it be useful?"
```

### Discovery Questions to Ask
- How many rooms/spaces do you currently manage?
- How many people on your team handle AV support?
- Can you troubleshoot remotely, or do you have to be on-site?
- When's your next major refresh or construction project?

### What to Listen For
- Team size relative to room count (understaffed = pain)
- Mentions of remote campus locations
- Complaints about travel time between buildings
- Construction projects or refresh cycles coming up

---

## Example 2: L&D Director Requests a Demo

**Scenario**: Sarah Chen, VP of Learning & Development at Salesforce, submitted a demo request form.

**Trigger**: `DEMO_REQUEST` (Highest Intent!)
**Persona**: `LD_DIRECTOR`

### Script Output

```
[ACKNOWLEDGE - 5 sec]
"Hi Sarah, this is Tim from Epiphan Video. Got your demo request -
let's get that scheduled."

[CONNECT - 10 sec]
"Before we book time, what's driving the interest? Is this about
scaling your training content production?"

[QUALIFY - 10 sec]
"Is this for a specific training initiative, or building a case for
self-service capture capability? What's your timeline?"

[PROPOSE - 5 sec]
"Perfect - I'll show you how OpenAI and similar companies use Pearl
for self-service SME capture. What works better, early or later this week?"
```

### Discovery Questions to Ask
- What training programs are you looking to scale?
- What's your current production capacity?
- Who else needs to see this to move forward?

### What to Listen For
- Specific training initiatives with deadlines
- Budget already allocated for training tech
- Stakeholder involvement hints

---

## Example 3: Technical Director Checks Pricing

**Scenario**: Mike Johnson, Media Director at Grace Community Church, visited the pricing page twice this week.

**Trigger**: `PRICING_PAGE`
**Persona**: `TECHNICAL_DIRECTOR`

### Script Output

```
[ACKNOWLEDGE - 5 sec]
"Hi Mike, this is Tim from Epiphan Video. I noticed you were looking
at our pricing page."

[CONNECT - 10 sec]
"Are you comparing us to PC-based solutions, or other hardware options?"

[QUALIFY - 10 sec]
"What's the scope - single venue or multiple locations? What features
are most important?"

[PROPOSE - 5 sec]
"Pearl Mini at $3,999 is a one-time cost with no subscriptions. Compare
that to ongoing software licenses and PC replacements. Want me to walk
you through the comparison?"
```

### Key Objection to Expect
**"Blackmagic is cheaper"**

Response: "ATEM needs a PC for recording. That PC can crash - we've all seen it. Pearl is standalone hardware that just works, even when volunteers operate it."

---

## Example 4: Simulation Director Attends Webinar

**Scenario**: Dr. Lisa Park, Simulation Center Director at Johns Hopkins, attended your "HIPAA-Compliant Simulation Recording" webinar.

**Trigger**: `WEBINAR_ATTENDED`
**Persona**: `SIMULATION_DIRECTOR`

### Script Output

```
[ACKNOWLEDGE - 5 sec]
"Hi Dr. Park, this is Tim from Epiphan Video. Thanks for attending our
HIPAA-Compliant Simulation Recording webinar - did the local recording
approach address your concerns?"

[CONNECT - 10 sec]
"Simulation directors at the webinar are usually worried about two things:
HIPAA compliance and accreditation documentation. Which is more pressing
for you?"

[QUALIFY - 10 sec]
"What's your current capture setup? Local or cloud-based?"

[PROPOSE - 5 sec]
"I can show you how Pearl integrates with SimCapture while keeping all
video on your network. Would that be helpful before your next accreditation
visit?"
```

### Discovery Questions to Ask
- What specifically caught your interest about the webinar?
- Do you use SimCapture or LearningSpace?
- What's your biggest challenge with debriefing?

### Key Objection to Expect
**"HIPAA concerns with video"**

Response: "Pearl records locally - video never touches cloud unless you choose. You control the data completely. That's why medical schools trust us."

---

## Example 5: Court Administrator Downloads Content

**Scenario**: Robert Williams, Court Administrator for Harris County, TX, downloaded your electronic court recording whitepaper.

**Trigger**: `CONTENT_DOWNLOAD`
**Persona**: `COURT_ADMINISTRATOR`

### Script Output

```
[ACKNOWLEDGE - 5 sec]
"Hi Robert, this is Tim from Epiphan Video. Thanks for downloading our
electronic court recording whitepaper - are you dealing with the court
reporter shortage?"

[CONNECT - 10 sec]
"Most court administrators who download that are trying to figure out
how to record hearings without enough court reporters. Is that your
situation?"

[QUALIFY - 10 sec]
"What percentage of your hearings have verbatim recording today? How
many courtrooms are you managing?"

[PROPOSE - 5 sec]
"33 states now permit electronic recording to address this. I can show
you how other courts are supplementing their court reporters. Would
that be useful?"
```

### Key Buying Signals
- "We can't find court reporters" → HIGH INTENT
- "Our backlog is X months for transcripts" → HIGH INTENT
- "What procurement vehicles are available?" → Medium intent

### Key Objection to Expect
**"Procurement is complex"**

Response: "We're on TIPS and Sourcewell for cooperative purchasing, plus GSA Schedule for federal. Makes it much simpler than full RFP."

---

## Example 6: L&D Director Visits Pricing (ROI Focus)

**Scenario**: David Kim, Training Director at Boeing, visited the pricing page after downloading the training ROI guide.

**Trigger**: `PRICING_PAGE`
**Persona**: `LD_DIRECTOR`

### Script Output

```
[ACKNOWLEDGE - 5 sec]
"Hi David, this is Tim from Epiphan Video. I noticed you were checking
out our pricing."

[CONNECT - 10 sec]
"Are you comparing us to ongoing production costs, or evaluating against
other capture solutions?"

[QUALIFY - 10 sec]
"What's the scope - single studio or multiple locations? How many content
creators would need access?"

[PROPOSE - 5 sec]
"Most L&D teams see ROI in the first year compared to outsourced production.
I can walk you through the comparison. Would that help?"
```

### Discovery Questions to Ask
- What are you spending annually on video production?
- How many training videos do you produce per year?
- What's your timeline for making a decision?

### What to Listen For
- Annual production spend (ROI comparison opportunity)
- Volume of content needed
- Budget timing

---

## How It Works: The Matrix

| When you know... | And they did... | You get... |
|------------------|-----------------|------------|
| AV Director | Content Download | NC State / fleet management pitch |
| AV Director | Demo Request | Fleet dashboard demo focus |
| L&D Director | Content Download | OpenAI / self-service pitch |
| L&D Director | Pricing Page | ROI vs. outsourcing comparison |
| Technical Director | Any trigger | Reliability + volunteer simplicity |
| Simulation Director | Any trigger | HIPAA compliance + local recording |
| Court Administrator | Any trigger | Court reporter shortage solution |

---

## Key Insight

**Before**: Same script for everyone who downloaded content
```
"Hi [Name], thanks for downloading our [content]. Are you evaluating solutions?"
```

**After**: Persona-specific messaging that speaks to THEIR pain
```
AV Director: "Most AV directors who download that are dealing with
             'too many rooms, too few people'..."

L&D Director: "Most L&D leaders who download that are trying to scale
              content creation without scaling their production budget..."
```

The difference: We're showing we understand their world before we pitch anything.

---

## API Usage (For Developers)

```python
from app.data.scripts import get_warm_script_for_call
from app.data.schemas import PersonaType, TriggerType

# Get persona-specific script
script = get_warm_script_for_call(
    trigger_type=TriggerType.CONTENT_DOWNLOAD,
    persona_type=PersonaType.AV_DIRECTOR
)

print(script["acknowledge"])  # The opening line
print(script["connect"])      # The pain-point bridge
print(script["qualify"])      # The qualification question
print(script["propose"])      # The CTA with reference story
print(script["discovery_questions"])  # Follow-up questions
print(script["source"])       # "persona_specific" or "trigger_generic"
```

If persona is unknown, it falls back to the generic trigger-based script.
