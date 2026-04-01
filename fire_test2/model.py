from huggingface_hub import hf_hub_download

hf_hub_download(
    repo_id="leeyunjai/yolo11-firedetect",
    filename="firedetect-11s.pt",
    local_dir="."
)