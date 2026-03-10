"""
Awareness Facts Engine
Provides educational facts about hair biology, growth science, and debunks myths.
Each fact now carries quiz_options and correct_answer for the Duolingo-style game loop.
"""

from typing import Dict, List, Optional


class AwarenessFactsEngine:
    """
    Generates categorised educational content about hair health with
    myth-busting, medical truths, and scientifically accurate information.
    Includes quiz options for each fact to power the in-app learning game.
    """

    def __init__(self):
        # ── Hair growth science facts ──────────────────────────────────────────
        self.hair_growth_science = [
            {
                "title": "Hair Growth Happens in Cycles",
                "description": "Hair grows in three phases: Anagen (growth), Catagen (transition), and Telogen (resting). At any time, 85–90% of your hair is in the growing phase.",
                "detail": "The anagen phase lasts 2–6 years, determining hair length. The catagen phase is a brief 2–3 week transition. The telogen phase lasts about 3 months before hair falls out and new growth begins.",
                "quiz_options": [
                    {"id": "a", "text": "Anagen → Catagen → Telogen"},
                    {"id": "b", "text": "Telogen → Anagen → Catagen"},
                    {"id": "c", "text": "There is only one phase"},
                    {"id": "d", "text": "Growth → Dormant → Dead"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Hair is the Fastest-Growing Tissue",
                "description": "After bone marrow, hair is the second fastest growing tissue in the human body.",
                "detail": "Hair grows approximately 0.5 inches (1.25 cm) per month, or about 6 inches per year. This growth rate can be influenced by age, health, and season.",
                "quiz_options": [
                    {"id": "a", "text": "Bone marrow — hair is second fastest"},
                    {"id": "b", "text": "Muscle — hair is slowest"},
                    {"id": "c", "text": "Liver cells — hair is third"},
                    {"id": "d", "text": "Hair is the absolute fastest"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Diet Impacts Hair Growth",
                "description": "Hair is made of protein (keratin), so adequate protein intake is essential for growth.",
                "detail": "Studies show that protein malnutrition can lead to hair loss. Essential fatty acids, vitamins (especially B vitamins, D, and iron) are also crucial for maintaining healthy hair growth cycles.",
                "quiz_options": [
                    {"id": "a", "text": "Protein (keratin) — it's the main building block"},
                    {"id": "b", "text": "Sugar — for energy to grow"},
                    {"id": "c", "text": "Calcium — the same as bones"},
                    {"id": "d", "text": "Vitamin C only"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Blood Flow Feeds Your Follicles",
                "description": "Hair follicles receive nutrients through blood vessels in the scalp.",
                "detail": "Poor circulation can limit nutrient delivery to hair follicles. Scalp massage, exercise, and proper posture can help improve blood flow to the scalp.",
                "quiz_options": [
                    {"id": "a", "text": "Improves nutrient delivery to follicles"},
                    {"id": "b", "text": "Has no effect on hair growth"},
                    {"id": "c", "text": "Only affects hair colour"},
                    {"id": "d", "text": "Causes hair to grow faster immediately"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Genetics Sets the Foundation",
                "description": "Your genes determine hair colour, texture, density, and predisposition to pattern hair loss.",
                "detail": "Androgenetic alopecia (pattern hair loss) is inherited and involves sensitivity to dihydrotestosterone (DHT), which shrinks hair follicles.",
                "quiz_options": [
                    {"id": "a", "text": "DHT sensitivity inherited from either parent"},
                    {"id": "b", "text": "Only from your mother's genes"},
                    {"id": "c", "text": "Genetics have no role in hair loss"},
                    {"id": "d", "text": "Only diet determines hair health"},
                ],
                "correct_answer": "a",
            },
        ]

        # ── Scalp biology facts ────────────────────────────────────────────────
        self.scalp_biology = [
            {
                "title": "Your Scalp Has ~100,000 Follicles",
                "description": "The average scalp contains approximately 100,000 to 150,000 hair follicles.",
                "detail": "Each follicle produces a single hair strand. The density varies by hair colour - blondes have the most (about 150,000), while redheads have the fewest (about 90,000).",
                "quiz_options": [
                    {"id": "a", "text": "100,000 – 150,000 follicles"},
                    {"id": "b", "text": "About 10,000 follicles"},
                    {"id": "c", "text": "Over 1 million follicles"},
                    {"id": "d", "text": "Exactly 50,000 follicles"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Sebum Keeps Hair Healthy",
                "description": "Sebaceous glands produce sebum, which moisturises and protects hair.",
                "detail": "Balanced sebum production keeps hair shiny and moisturised. Overproduction can lead to oily hair, while underproduction causes dryness and brittleness.",
                "quiz_options": [
                    {"id": "a", "text": "Sebaceous glands produce it naturally"},
                    {"id": "b", "text": "You must apply conditioner daily"},
                    {"id": "c", "text": "Only water hydrates hair"},
                    {"id": "d", "text": "Hair produces its own oil through the shaft"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Scalp pH Should Be 4.5–5.5",
                "description": "A healthy scalp has a slightly acidic pH of 4.5–5.5.",
                "detail": "This acidic environment helps protect against harmful bacteria and fungi. Using harsh alkaline products can disrupt this balance and lead to scalp issues.",
                "quiz_options": [
                    {"id": "a", "text": "4.5 – 5.5 (slightly acidic)"},
                    {"id": "b", "text": "7.0 (neutral like water)"},
                    {"id": "c", "text": "9.0 (alkaline)"},
                    {"id": "d", "text": "pH doesn't matter for scalp health"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Dandruff is Accelerated Cell Turnover",
                "description": "Scalp cells renew every 28 days. When inflamed, they shed faster — causing visible flakes.",
                "detail": "When this process speeds up due to irritation or inflammation, visible flaking (dandruff) occurs. Keeping the scalp calm and balanced supports normal cell turnover.",
                "quiz_options": [
                    {"id": "a", "text": "Accelerated scalp cell turnover causing flakes"},
                    {"id": "b", "text": "Caused by washing hair too often"},
                    {"id": "c", "text": "A sign of hair growing too fast"},
                    {"id": "d", "text": "Only occurs in people with oily hair"},
                ],
                "correct_answer": "a",
            },
        ]

        # ── Lifestyle impact facts ─────────────────────────────────────────────
        self.lifestyle_impact = [
            {
                "title": "Stress Triggers Hair Loss",
                "description": "Telogen effluvium is a type of hair loss caused by severe stress or trauma — typically appearing 2–3 months after the event.",
                "detail": "Stress pushes hair follicles prematurely into the resting phase. Hair typically sheds 2–3 months after the stressful event. Managing stress is crucial for hair health.",
                "quiz_options": [
                    {"id": "a", "text": "2–3 months after the stressful event"},
                    {"id": "b", "text": "Immediately during the stress"},
                    {"id": "c", "text": "After 2 years of chronic stress only"},
                    {"id": "d", "text": "Stress has no impact on hair shedding"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Sleep Repairs Hair Follicles",
                "description": "During sleep, the body releases growth hormone which is critical for follicle repair and regeneration.",
                "detail": "Growth hormone is primarily secreted during deep sleep. Lack of sleep can disrupt this process and negatively impact hair health.",
                "quiz_options": [
                    {"id": "a", "text": "Growth hormone release during deep sleep"},
                    {"id": "b", "text": "Hair grows only while you're awake"},
                    {"id": "c", "text": "Sleep has no connection to hair biology"},
                    {"id": "d", "text": "Only diet matters for follicle repair"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Exercise Boosts Scalp Circulation",
                "description": "Regular physical activity increases blood flow to the scalp, delivering more nutrients to follicles.",
                "detail": "Improved blood flow means more nutrients delivered to hair follicles. However, excessive sweating should be followed by proper hair cleansing.",
                "quiz_options": [
                    {"id": "a", "text": "Increases blood flow and nutrient delivery to follicles"},
                    {"id": "b", "text": "Causes hair loss through sweat"},
                    {"id": "c", "text": "Has no measurable effect on hair"},
                    {"id": "d", "text": "Only cardio exercise affects hair growth"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Smoking Damages Hair Follicles",
                "description": "Smoking reduces blood flow to the scalp and introduces toxins that damage follicles.",
                "detail": "Studies show smoking is associated with increased risk of pattern hair loss. Quitting smoking can improve overall hair health.",
                "quiz_options": [
                    {"id": "a", "text": "Restricts blood flow and introduces follicle-damaging toxins"},
                    {"id": "b", "text": "Protects hair from UV damage"},
                    {"id": "c", "text": "Has no connection to hair loss"},
                    {"id": "d", "text": "Only affects lung health"},
                ],
                "correct_answer": "a",
            },
        ]

        # ── Myth busters ───────────────────────────────────────────────────────
        self.myth_busters = [
            {
                "statement": "Cutting hair makes it grow faster",
                "correct_answer": "False",
                "explanation": "Hair grows from the follicles, not the ends. Trimming split ends prevents breakage but doesn't affect growth rate. Hair grows about half an inch per month regardless of cutting.",
            },
            {
                "statement": "Shaving makes hair grow back thicker",
                "correct_answer": "False",
                "explanation": "Shaving doesn't change hair thickness or growth rate. What changes is the hair tip — shaved hair has a blunt tip that may feel coarser, but it's the same hair that would have grown anyway.",
            },
            {
                "statement": "More shampoo = healthier hair",
                "correct_answer": "False",
                "explanation": "Over-washing strips natural oils that protect hair. Most people only need to shampoo every 2–3 days. Frequency depends on hair type and lifestyle.",
            },
            {
                "statement": "Hair loss is always genetic",
                "correct_answer": "False",
                "explanation": "While genetics play a role in pattern hair loss, many other factors can cause hair loss including stress, nutritional deficiencies, medical conditions, medications, and hormonal changes.",
            },
            {
                "statement": "Expensive hair products work better",
                "correct_answer": "False",
                "explanation": "Price doesn't indicate effectiveness. Many affordable products contain the same active ingredients as expensive ones. What matters is finding products suited to your hair type and needs.",
            },
            {
                "statement": "You can block DHT naturally",
                "correct_answer": "Partially True",
                "explanation": "Some foods and supplements may have mild DHT-blocking properties (like saw palmetto, pumpkin seed oil), but they're generally less effective than prescription treatments like finasteride.",
            },
        ]

        # ── Medical truths ─────────────────────────────────────────────────────
        self.medical_truths = [
            {
                "title": "Minoxidil is Proven Effective",
                "description": "Minoxidil is the only FDA-approved over-the-counter topical treatment for hair loss.",
                "detail": "It works by prolonging the anagen (growth) phase and widening hair follicles. Results typically appear after 4–6 months of consistent use. Must be continued indefinitely to maintain results.",
                "quiz_options": [
                    {"id": "a", "text": "4–6 months of consistent use"},
                    {"id": "b", "text": "2 weeks of use"},
                    {"id": "c", "text": "Results are immediate"},
                    {"id": "d", "text": "It never works for everyone"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Finasteride Requires a Prescription",
                "description": "Finasteride is a prescription medication that blocks DHT, the hormone causing pattern hair loss.",
                "detail": "It's highly effective for male pattern baldness but has potential side effects. Women of childbearing age should not handle broken tablets due to birth defect risk.",
                "quiz_options": [
                    {"id": "a", "text": "Blocks DHT to slow pattern hair loss"},
                    {"id": "b", "text": "It grows new follicles from scratch"},
                    {"id": "c", "text": "It is available over the counter"},
                    {"id": "d", "text": "Works the same as minoxidil"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Iron Deficiency Causes Hair Loss",
                "description": "Iron deficiency anaemia is a common cause of hair loss, especially in women.",
                "detail": "Ferritin levels (stored iron) correlate with hair loss severity. Getting blood work done to check iron levels is important if experiencing unexpected hair loss.",
                "quiz_options": [
                    {"id": "a", "text": "Check ferritin levels with a blood test"},
                    {"id": "b", "text": "Iron has no connection to hair health"},
                    {"id": "c", "text": "Only women with anaemia lose hair"},
                    {"id": "d", "text": "Iron supplements always cause hair loss"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Thyroid Problems Affect Hair",
                "description": "Both hyperthyroidism and hypothyroidism can cause hair loss.",
                "detail": "Thyroid hormones regulate many body functions including hair growth. Treating the underlying thyroid condition usually resolves associated hair loss.",
                "quiz_options": [
                    {"id": "a", "text": "Both over- and under-active thyroid can cause hair loss"},
                    {"id": "b", "text": "Only hypothyroidism affects hair"},
                    {"id": "c", "text": "Thyroid has no effect on hair follicles"},
                    {"id": "d", "text": "Only hyperthyroidism causes hair loss"},
                ],
                "correct_answer": "a",
            },
            {
                "title": "Some Hairstyles Cause Permanent Loss",
                "description": "Traction alopecia from tight hairstyles can cause permanent hair loss if untreated.",
                "detail": "Constant pulling on hair follicles from tight ponytails, braids, or weaves can cause scarring and permanent damage. Giving hair breaks and avoiding tight styles prevents this.",
                "quiz_options": [
                    {"id": "a", "text": "Yes — follicle scarring can become permanent"},
                    {"id": "b", "text": "No — follicles always recover from tension"},
                    {"id": "c", "text": "Only chemical treatments cause permanent loss"},
                    {"id": "d", "text": "Traction only affects hair texture"},
                ],
                "correct_answer": "a",
            },
        ]

    def generate(
        self, hair_severity: Optional[str] = None, root_cause: Optional[str] = None
    ) -> Dict:
        """
        Generate categorised facts with quiz options for the Duolingo-style game loop.

        Args:
            hair_severity: Current hair loss severity (optional, for personalisation)
            root_cause:    Primary root cause (optional, for personalisation)

        Returns:
            Dictionary with categorised facts and quiz data.
        """
        result = {
            "hair_growth_science": self.hair_growth_science.copy(),
            "scalp_biology":       self.scalp_biology.copy(),
            "lifestyle_impact":    self.lifestyle_impact.copy(),
            "myth_busters":        self.myth_busters.copy(),
            "medical_truths":      self.medical_truths.copy(),
        }

        # Severity-based personalisation note
        if hair_severity and hair_severity.lower() in ["severe", "high"]:
            result["personalization_note"] = (
                "Given your severity level, we recommend focusing on the "
                "medical_truths and consulting a dermatologist for professional treatment."
            )

        return result

    def get_fact_categories(self) -> List[str]:
        """Get list of available fact categories."""
        return [
            "hair_growth_science",
            "scalp_biology",
            "lifestyle_impact",
            "myth_busters",
            "medical_truths",
        ]

    def get_quiz_questions(self, category: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """
        Return quiz-ready questions from facts that have quiz_options defined.

        Args:
            category: Optional filter ('hair_growth_science', 'scalp_biology', etc.)
            limit:    Max number of questions to return.
        """
        import random
        pool = []
        sources = {
            "hair_growth_science": self.hair_growth_science,
            "scalp_biology":       self.scalp_biology,
            "lifestyle_impact":    self.lifestyle_impact,
            "medical_truths":      self.medical_truths,
        }

        if category and category in sources:
            candidates = sources[category]
        else:
            candidates = [f for facts in sources.values() for f in facts]

        for fact in candidates:
            if "quiz_options" in fact and "correct_answer" in fact:
                pool.append({
                    "question":       fact["description"],
                    "explanation":    fact.get("detail", ""),
                    "options":        fact["quiz_options"],
                    "correct_answer": fact["correct_answer"],
                    "category":       category or "mixed",
                    "xp_reward":      20,
                })

        random.shuffle(pool)
        return pool[:limit]


def create_awareness_facts_engine() -> AwarenessFactsEngine:
    """Factory function to create AwarenessFactsEngine instance."""
    return AwarenessFactsEngine()


if __name__ == "__main__":
    engine = AwarenessFactsEngine()

    result = engine.generate(hair_severity="moderate")

    print("Awareness Facts (with quiz options):")
    print("\nHair Growth Science:")
    for fact in result["hair_growth_science"][:2]:
        print(f"  Fact:    {fact['title']}")
        print(f"  Quiz:    {fact['description'][:60]}...")
        if "quiz_options" in fact:
            for opt in fact["quiz_options"]:
                marker = "✓" if opt["id"] == fact["correct_answer"] else " "
                print(f"    [{marker}] {opt['id']}: {opt['text']}")
        print()

    print("\nMyth Busters:")
    for myth in result["myth_busters"][:2]:
        print(f"  Myth:  {myth['statement']}")
        print(f"  Fact:  {myth['correct_answer']} — {myth['explanation'][:60]}...")
        print()

    quiz_qs = engine.get_quiz_questions(limit=3)
    print(f"\nSample Quiz Questions ({len(quiz_qs)} generated):")
    for q in quiz_qs:
        print(f"  Q: {q['question'][:70]}...")