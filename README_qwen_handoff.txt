Qwen is the decision layer after the detector.

Input to Qwen:
Detector JSON such as smoke_detected, fire_detected, smoke_confidence, fire_confidence, repeated_frames.

Output from Qwen:
{
  "detected_event": "",
  "alert_level": "",
  "dispatch_recommendation": "",
  "reasoning": "",
  "operator_message": ""
}

Backend rule:
emergency = alert_level in ["high", "critical"]

Notes:
- Qwen does not detect smoke or fire itself.
- Qwen only decides severity and recommended action.
- Qwen should only use fields present in the detector input.
- Qwen should not mention false positives unless detector input explicitly says so.