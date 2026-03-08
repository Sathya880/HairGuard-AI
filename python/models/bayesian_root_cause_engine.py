"""
Bayesian Network Root Cause Engine
===================================
Implements a directed probabilistic graphical model (Bayesian Network) that
reasons about hair-loss root causes the way a clinician would: signals flow
through a causal graph rather than being scored independently.

Node hierarchy
──────────────
EVIDENCE LAYER  (observed signals, set from image models + lifestyle)
  ├── hair_loss_severity        : none|mild|moderate|severe|very_severe
  ├── dandruff_severity         : none|mild|moderate|severe
  ├── scalp_inflammation        : low|moderate|high    (derived from dandruff)
  ├── hair_density_loss         : normal|moderate|severe (from image model)
  ├── stress_level              : low|moderate|high     (from lifestyle)
  ├── sleep_quality             : good|fair|poor
  ├── diet_quality              : good|fair|poor
  ├── hormonal_signal           : low|moderate|high   (inferred from age/pattern)
  └── genetic_signal            : absent|present      (from flashcard family_history)

LATENT / CAUSE LAYER  (what we're inferring)
  ├── androgenetic_alopecia     (genetic + hormonal node)
  ├── telogen_effluvium         (stress + diet + sleep node)
  ├── scalp_inflammation_cause  (dandruff + helmet + sweat node)
  ├── nutritional_deficiency    (diet + lifestyle node)
  └── traction_mechanical       (helmet + heat_styling node)

Each cause node holds a Conditional Probability Table (CPT) expressed as a
float score that is then normalised across all causes to produce posterior
probabilities.  The engine returns:
  - primary_cause        : str
  - secondary_cause      : str
  - causes               : List[{name, probability, supporting_factors}]
  - confidence_percent   : float   (probability of primary cause × 100)
  - data_strength        : Weak | Moderate | Strong
  - network_summary      : human-readable explanation
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import math


# ─── Severity encoders ────────────────────────────────────────────────────────

_HAIRLOSS_SEVERITY = {
    "none": 0.0, "low": 0.10, "mild": 0.30,
    "moderate": 0.55, "high": 0.75, "severe": 0.90, "very_severe": 1.0,
}
_DANDRUFF_SEVERITY = {
    "none": 0.0, "low": 0.15, "mild": 0.30,
    "moderate": 0.55, "severe": 0.90,
}
_LIFESTYLE_FLASHCARDS = {
    "stress": {
        "Very high": 1.0, "High": 0.80, "Moderate": 0.50,
        "Low": 0.20, "I don't feel stressed": 0.05,
    },
    "sleep": {
        "Less than 6 hours": 1.0, "Irregular sleep schedule": 0.90,
        "6–7 hours": 0.45, "7–8 hours": 0.10,
    },
    "diet": {
        "Very irregular meals": 1.0, "Mostly fast food / junk food": 0.80,
        "Mostly home food but irregular": 0.45, "Balanced and nutritious": 0.05,
    },
    "family_history": {
        "Yes": 1.0, "Not sure": 0.45, "No": 0.0,
    },
    "helmet_usage": {
        "Yes, daily": 1.0, "Yes, occasionally": 0.55,
        "Rarely": 0.20, "Never": 0.0,
    },
    "scalp_sweat": {
        "Yes, a lot": 1.0, "Moderate sweating": 0.55,
        "Very little": 0.10, "Not sure": 0.30,
    },
    "heat_styling": {
        "Daily": 1.0, "Frequently": 0.75, "Occasionally": 0.40,
        "Rarely": 0.15, "Never": 0.0,
    },
    "water_type": {
        "Hard water": 0.80, "Tap water": 0.45,
        "Filtered water": 0.10, "Soft water": 0.0,
    },
    "hair_wash": {
        "Daily": 0.70, "Every other day": 0.40,
        "Twice a week": 0.15, "Once a week": 0.05, "Rarely": 0.30,
    },
    # Age: younger = higher TE risk; older = higher AGA risk
    "age": {
        "Under 20": 0.10, "20–30": 0.30, "31–40": 0.55,
        "41–50": 0.75, "Over 50": 0.90,
    },
    # Gender: male has stronger AGA/DHT predisposition
    "gender": {
        "Male": 1.0, "Female": 0.45, "Other": 0.50,
    },
    # Problem duration: chronic → more likely AGA; acute → more likely TE
    "problem_duration": {
        "Less than 1 month": 0.15, "1–3 months": 0.35,
        "3–6 months": 0.55, "6–12 months": 0.70,
        "More than 1 year": 0.90,
    },
}


def _enc(key: str, value: Optional[str], default: float = 0.30) -> float:
    """Encode a flashcard answer to [0, 1]."""
    if not value:
        return default
    return _LIFESTYLE_FLASHCARDS.get(key, {}).get(value, default)


def _hairloss_enc(sev: Optional[str]) -> float:
    return _HAIRLOSS_SEVERITY.get((sev or "none").lower(), 0.0)


def _dandruff_enc(sev: Optional[str]) -> float:
    return _DANDRUFF_SEVERITY.get((sev or "none").lower(), 0.0)


# ─── Bayesian Node ────────────────────────────────────────────────────────────

@dataclass
class CauseNode:
    name: str
    display_name: str
    score: float = 0.0
    probability: float = 0.0
    supporting_factors: List[str] = field(default_factory=list)

    def add_evidence(self, weight: float, factor_desc: str) -> None:
        self.score += weight
        if factor_desc:
            self.supporting_factors.append(factor_desc)


# ─── Main engine ──────────────────────────────────────────────────────────────

class BayesianRootCauseEngine:
    """
    Directed probabilistic graphical model for hair-loss root cause inference.

    The network is structured as:

      [Evidence nodes] → CPT weights → [Cause nodes] → Normalised posteriors

    CPT (Conditional Probability Table) weights are expert-derived and reflect
    known clinical evidence:
      - Genetic / androgenetic alopecia is the most common cause in men (AGA).
      - Telogen effluvium is tightly linked to stress, sleep deprivation, diet.
      - Scalp inflammation is driven by dandruff, occlusion (helmet), sweat.
      - Nutritional deficiency is a diet / lifestyle signal.
      - Traction / mechanical damage is from heat styling and helmet occlusion.
    """

    # ── CPT weights ──────────────────────────────────────────────────────────
    # Each tuple: (evidence_node_key, CPT_weight_to_cause)
    # Weights are NOT arbitrary—they reflect clinical literature order-of-magnitude
    # relationships between signals and causes.

    _CPT: Dict[str, List[Tuple[str, float]]] = {
        "androgenetic_alopecia": [
            ("genetic_signal",        0.40),   # family history — strongest predictor
            ("hormonal_signal",       0.25),   # crown + frontal pattern (DHT zones)
            ("age_signal",            0.15),   # older age = higher AGA prevalence
            ("gender_signal",         0.10),   # male = stronger DHT sensitivity
            ("duration_signal",       0.10),   # chronic/long duration → AGA not TE
        ],
        "telogen_effluvium": [
            ("stress_level",          0.30),   # acute stress → diffuse shedding
            ("sleep_quality",         0.22),   # sleep deprivation → cortisol spike
            ("diet_quality",          0.22),   # caloric/protein deficit → TE
            ("hair_loss_severity",    0.16),   # TE = moderate diffuse loss
            ("duration_signal_inv",   0.10),   # short duration → more likely TE
        ],
        "scalp_inflammation": [
            ("dandruff_severity",     0.38),   # dandruff = primary inflammation marker
            ("scalp_occlusion",       0.27),   # helmet occlusion traps fungi
            ("scalp_sweat",           0.20),   # sweat = malassezia substrate
            ("water_type_signal",     0.08),   # hard water irritates scalp
            ("hair_loss_severity",    0.07),   # secondary hair loss from inflammation
        ],
        "nutritional_deficiency": [
            ("diet_quality",          0.50),   # poor diet = nutrient depletion
            ("stress_level",          0.18),   # stress depletes B-vitamins, zinc
            ("sleep_quality",         0.12),   # poor sleep → reduced nutrient absorption
            ("hair_loss_severity",    0.20),   # deficiency causes diffuse thinning
        ],
        "traction_mechanical": [
            ("mechanical_stress",     0.45),   # heat styling + helmet
            ("scalp_occlusion",       0.28),   # prolonged occlusion
            ("hair_loss_severity",    0.15),   # damage-pattern loss
            ("dandruff_severity",     0.12),   # friction → scalp irritation
        ],
    }

    _DISPLAY_NAMES = {
        "androgenetic_alopecia": "Androgenetic Alopecia (Genetic/Hormonal)",
        "telogen_effluvium":     "Telogen Effluvium (Stress-Induced Shedding)",
        "scalp_inflammation":    "Scalp Inflammation",
        "nutritional_deficiency":"Nutritional Deficiency",
        "traction_mechanical":   "Traction / Mechanical Damage",
    }

    def __init__(self):
        self.nodes: Dict[str, CauseNode] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def infer(
        self,
        hairloss: Dict,
        dandruff: Dict,
        flashcard_answers: Dict[str, str],
        lifestyle_result: Optional[Dict] = None,
    ) -> Dict:
        """
        Run Bayesian inference and return root cause posterior probabilities.

        Parameters
        ----------
        hairloss : dict
            Image-model output. Expected keys: overallSeverity, severity,
            combinedDamage, views (top/front/back severity).
        dandruff : dict
            Image-model output. Expected key: severity.
        flashcard_answers : dict
            Lifestyle flashcard answers keyed by question slug.
        lifestyle_result : dict, optional
            Pre-computed lifestyle analysis from LifestyleAnalyzer.

        Returns
        -------
        dict with keys:
            primary_cause, secondary_cause, causes, confidence_percent,
            impact_breakdown, data_strength, network_summary
        """

        # ── 1. Build evidence layer ───────────────────────────────────────────
        evidence = self._build_evidence(
            hairloss, dandruff, flashcard_answers, lifestyle_result or {}
        )

        # ── 2. Propagate through CPT ──────────────────────────────────────────
        self.nodes = {}
        for cause_key, cpt_edges in self._CPT.items():
            node = CauseNode(
                name=cause_key,
                display_name=self._DISPLAY_NAMES[cause_key],
            )
            for evidence_key, weight in cpt_edges:
                ev_value = evidence.get(evidence_key, 0.0)
                contribution = ev_value * weight
                node.add_evidence(
                    weight=contribution,
                    factor_desc=self._factor_label(evidence_key, ev_value)
                    if ev_value > 0.25
                    else "",
                )
            self.nodes[cause_key] = node

        # ── 3. Apply prior boost for genetic when family history is absent ─────
        # Without explicit "Yes" on family history, AGA prior drops moderately.
        family_signal = evidence.get("genetic_signal", 0.0)
        if family_signal < 0.1:
            self.nodes["androgenetic_alopecia"].score *= 0.40

        # ── 4. Normalise to posterior probabilities ───────────────────────────
        total_score = sum(n.score for n in self.nodes.values())
        if total_score > 0:
            for node in self.nodes.values():
                node.probability = node.score / total_score
        else:
            # Uniform fallback
            p = 1.0 / len(self.nodes)
            for node in self.nodes.values():
                node.probability = p

        # ── 5. Apply Laplace smoothing (prevent zero posteriors) ──────────────
        smoothing = 0.02
        for node in self.nodes.values():
            node.probability = (node.probability + smoothing) / (1 + smoothing * len(self.nodes))

        # Re-normalise after smoothing
        total = sum(n.probability for n in self.nodes.values())
        for node in self.nodes.values():
            node.probability /= total

        # ── 6. Sort by posterior ──────────────────────────────────────────────
        sorted_nodes = sorted(
            self.nodes.values(), key=lambda n: n.probability, reverse=True
        )

        primary_node = sorted_nodes[0]
        secondary_node = sorted_nodes[1] if len(sorted_nodes) > 1 else primary_node

        confidence_percent = round(primary_node.probability * 100, 1)

        # ── 7. Build cause list for UI ────────────────────────────────────────
        causes_list = [
            {
                "name": n.display_name,
                "key": n.name,
                "probability": round(n.probability * 100, 1),
                "supporting_factors": [f for f in n.supporting_factors if f],
                "data_strength": self._data_strength(flashcard_answers),
            }
            for n in sorted_nodes
        ]

        # ── 8. Impact breakdown (compatible with existing UI) ─────────────────
        impact_breakdown = {
            n.display_name: round(n.probability, 4) for n in sorted_nodes
        }

        # ── 9. Network summary ────────────────────────────────────────────────
        network_summary = self._generate_summary(
            primary_node, secondary_node, evidence, confidence_percent
        )

        return {
            "primary_cause": primary_node.display_name,
            "secondary_cause": secondary_node.display_name,
            "confidence_percent": confidence_percent,
            "impact_breakdown": impact_breakdown,
            "causes": causes_list,
            "data_strength": self._data_strength(flashcard_answers),
            "network_summary": network_summary,
            # Legacy keys for backward compat
            "primary": primary_node.display_name,
            "secondary": secondary_node.display_name,
            "details": impact_breakdown,
        }

    # ── Evidence builder ──────────────────────────────────────────────────────

    def _build_evidence(
        self,
        hairloss: Dict,
        dandruff: Dict,
        flashcard_answers: Dict,
        lifestyle_result: Dict,
    ) -> Dict[str, float]:
        """
        Map raw signals onto the evidence layer [0, 1].
        """

        # Hair loss severity (from image model)
        hl_overall = (
            hairloss.get("overallSeverity")
            or hairloss.get("severity")
            or hairloss.get("overall_severity", "none")
        )
        hl_val = _hairloss_enc(hl_overall)

        # View-wise: use the worst view as additional signal
        views = hairloss.get("views", {})
        hl_top   = _hairloss_enc(views.get("top", {}).get("severity"))
        hl_front = _hairloss_enc(views.get("front", {}).get("severity"))
        hl_back  = _hairloss_enc(views.get("back", {}).get("severity"))
        hl_max   = max(hl_val, hl_top, hl_front, hl_back)

        # Dandruff severity (from image model)
        dd_val = _dandruff_enc(dandruff.get("severity"))

        # Scalp occlusion (helmet + sweat combined node)
        helmet  = _enc("helmet_usage", flashcard_answers.get("helmet_usage"), 0.1)
        sweat   = _enc("scalp_sweat",  flashcard_answers.get("scalp_sweat"),  0.1)
        occlusion = min((helmet * 0.6 + sweat * 0.4), 1.0)

        # Mechanical stress (heat styling + helmet)
        heat      = _enc("heat_styling", flashcard_answers.get("heat_styling"), 0.1)
        mechanical = min((heat * 0.7 + helmet * 0.3), 1.0)

        # Lifestyle signals
        stress_raw = flashcard_answers.get("stress") or flashcard_answers.get("stress_level")
        sleep_raw  = flashcard_answers.get("sleep")  or flashcard_answers.get("sleep_duration")
        diet_raw   = flashcard_answers.get("diet")   or flashcard_answers.get("diet_quality")

        stress  = _enc("stress", stress_raw, 0.35)
        sleep   = _enc("sleep",  sleep_raw,  0.35)
        diet    = _enc("diet",   diet_raw,   0.35)

        # If lifestyle_result already computed overall_score, use it to refine
        lifestyle_score = lifestyle_result.get("overall_score") or lifestyle_result.get("score", 50)
        lifestyle_risk = max(0.0, min(1.0, (100 - lifestyle_score) / 100))
        # Blend raw signals with lifestyle risk as a prior
        stress = stress * 0.7 + lifestyle_risk * 0.3
        diet   = diet   * 0.7 + lifestyle_risk * 0.3

        # Genetic signal
        genetic = _enc("family_history", flashcard_answers.get("family_history"), 0.25)

        # Age signal — older increases AGA probability
        age_raw = flashcard_answers.get("age") or flashcard_answers.get("age_range")
        age_signal = _enc("age", age_raw, 0.40)

        # Gender signal — male has stronger DHT/AGA predisposition
        gender_raw = flashcard_answers.get("gender")
        gender_signal = _enc("gender", gender_raw, 0.60)

        # Problem duration — chronic loss → AGA; acute → TE
        duration_raw = flashcard_answers.get("problem_duration") or flashcard_answers.get("duration")
        duration_signal = _enc("problem_duration", duration_raw, 0.45)
        # Inverted for TE (short duration = higher TE likelihood)
        duration_inv = 1.0 - duration_signal

        # Water type signal for scalp inflammation
        water_raw = flashcard_answers.get("water_type") or flashcard_answers.get("water")
        water_signal = _enc("water_type", water_raw, 0.30)

        # Hormonal proxy: combination of genetic signal + pattern of frontal/crown loss + age + gender
        hl_crown   = _hairloss_enc(views.get("top", {}).get("severity"))
        hl_frontal = _hairloss_enc(views.get("front", {}).get("severity"))
        hormonal   = min(
            (genetic * 0.35 + hl_crown * 0.25 + hl_frontal * 0.20
             + age_signal * 0.10 + gender_signal * 0.10),
            1.0
        )

        return {
            "hair_loss_severity":  hl_max,
            "dandruff_severity":   dd_val,
            "scalp_inflammation":  min(dd_val * 0.7 + occlusion * 0.3, 1.0),
            "scalp_occlusion":     occlusion,
            "mechanical_stress":   mechanical,
            "stress_level":        stress,
            "sleep_quality":       sleep,
            "diet_quality":        diet,
            "genetic_signal":      genetic,
            "hormonal_signal":     hormonal,
            "scalp_sweat":         sweat,
            "age_signal":          age_signal,
            "gender_signal":       gender_signal,
            "duration_signal":     duration_signal,
            "duration_signal_inv": duration_inv,
            "water_type_signal":   water_signal,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _factor_label(key: str, value: float) -> str:
        labels = {
            "genetic_signal":      "Family history of hair loss",
            "hormonal_signal":     "Hormonal pattern (crown/frontal loss)",
            "hair_loss_severity":  "Observed hair loss severity",
            "dandruff_severity":   "Dandruff / scalp flaking",
            "scalp_inflammation":  "Scalp inflammation",
            "scalp_occlusion":     "Scalp occlusion (helmet/sweat)",
            "scalp_sweat":         "Excessive scalp sweating",
            "mechanical_stress":   "Heat/mechanical styling stress",
            "stress_level":        "High stress level",
            "sleep_quality":       "Poor sleep quality",
            "diet_quality":        "Poor diet quality",
            "age_signal":          "Age-related hair loss risk",
            "gender_signal":       "Gender-related DHT sensitivity",
            "duration_signal":     "Chronic / long-duration hair loss",
            "duration_signal_inv": "Recent / acute onset hair loss",
            "water_type_signal":   "Hard water scalp irritation",
        }
        return labels.get(key, key.replace("_", " ").title())

    @staticmethod
    def _data_strength(flashcard_answers: Dict) -> str:
        n = len([v for v in flashcard_answers.values() if v])
        if n >= 6:
            return "Strong"
        if n >= 3:
            return "Moderate"
        return "Weak"

    @staticmethod
    def _generate_summary(
        primary: CauseNode,
        secondary: CauseNode,
        evidence: Dict[str, float],
        confidence: float,
    ) -> str:
        lines = []
        lines.append(
            f"Bayesian analysis identified {primary.display_name} as the most "
            f"probable root cause ({confidence:.1f}% posterior probability)."
        )

        if primary.supporting_factors:
            lines.append(
                "Key contributing signals: "
                + ", ".join(primary.supporting_factors[:3]) + "."
            )

        if secondary.probability > 0.15:
            lines.append(
                f"{secondary.display_name} is a notable secondary contributor "
                f"({secondary.probability * 100:.1f}%), especially if primary "
                f"interventions do not yield improvement within 4–6 weeks."
            )

        # Network reasoning
        hl = evidence.get("hair_loss_severity", 0)
        stress = evidence.get("stress_level", 0)
        if hl > 0.5 and stress > 0.5:
            lines.append(
                "The network detected co-activation of the stress and hair-loss "
                "severity nodes, increasing the probability of Telogen Effluvium "
                "as a concurrent process."
            )

        genetic = evidence.get("genetic_signal", 0)
        if genetic > 0.7:
            lines.append(
                "Strong genetic signal detected. Even with lifestyle improvements, "
                "Androgenetic Alopecia may require medical management."
            )

        age = evidence.get("age_signal", 0)
        gender = evidence.get("gender_signal", 0)
        if age > 0.6 and gender > 0.8:
            lines.append(
                "Age and gender profile aligns with higher androgenetic risk. "
                "DHT-mediated follicle miniaturization is the likely mechanism."
            )

        duration = evidence.get("duration_signal", 0)
        if duration < 0.3 and stress > 0.5:
            lines.append(
                "Recent onset combined with elevated stress suggests a Telogen Effluvium "
                "trigger event within the last 2–4 months."
            )

        dandruff = evidence.get("dandruff_severity", 0)
        occlusion = evidence.get("scalp_occlusion", 0)
        if dandruff > 0.5 and occlusion > 0.5:
            lines.append(
                "Scalp occlusion combined with dandruff severity indicates active "
                "fungal/inflammatory activity that may be accelerating hair loss."
            )

        return " ".join(lines)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_bayesian_engine() -> BayesianRootCauseEngine:
    return BayesianRootCauseEngine()


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = BayesianRootCauseEngine()

    result = engine.infer(
        hairloss={
            "overallSeverity": "moderate",
            "views": {
                "top":   {"severity": "moderate"},
                "front": {"severity": "mild"},
                "back":  {"severity": "mild"},
            },
        },
        dandruff={"severity": "moderate"},
        flashcard_answers={
            "family_history": "Yes",
            "stress":         "Very high",
            "sleep":          "Less than 6 hours",
            "diet":           "Mostly fast food / junk food",
            "helmet_usage":   "Never",
            "scalp_sweat":    "Moderate sweating",
        },
        lifestyle_result={"overall_score": 42},
    )

    print("=== Bayesian Root Cause Result ===")
    print(f"Primary  : {result['primary_cause']}  ({result['confidence_percent']}%)")
    print(f"Secondary: {result['secondary_cause']}")
    print(f"Data Strength: {result['data_strength']}")
    print(f"\nSummary: {result['network_summary']}")
    print("\nAll causes:")
    for c in result["causes"]:
        print(f"  {c['name']:45s}  {c['probability']:5.1f}%  |  {c['supporting_factors']}")