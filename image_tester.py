"""
image_tester.py - 이미지 생성 품질 비교 테스터
다양한 모델 × 프롬프트 프리셋 조합을 시각적으로 비교
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from PIL import Image, ImageTk
import requests
from urllib.parse import quote
import threading
import time
import io

# ============================================================
# 프롬프트 프리셋
# ============================================================
PRESETS = {
    "실사-시네마틱": (
        "A cinematic widescreen photograph taken with a Sony A7R IV camera, "
        "85mm f/1.4 lens, shallow depth of field, golden hour natural lighting, "
        "photorealistic, ultra high definition 8K, film grain, "
        "{scene}. No text, no watermarks, no logos."
    ),
    "실사-다큐멘터리": (
        "A professional documentary-style photograph, "
        "shot on location with natural lighting, Canon EOS R5, "
        "wide angle 24mm lens, vivid true-to-life colors, "
        "{scene}. No text, no watermarks, no logos."
    ),
    "실사-항공촬영": (
        "An aerial drone photograph taken from above, DJI Mavic 3 Pro, "
        "sweeping landscape view, golden hour, ultra sharp details, "
        "photorealistic, National Geographic quality, "
        "{scene}. No text, no watermarks, no logos."
    ),
    "일러스트-지브리": (
        "A beautiful Studio Ghibli anime style illustration, "
        "hand-painted watercolor textures, soft pastel colors, "
        "dreamy atmospheric lighting, Hayao Miyazaki inspired, "
        "{scene}. No text, no watermarks."
    ),
    "일러스트-디즈니": (
        "A Disney Pixar 3D animation style render, "
        "vibrant saturated colors, soft ambient occlusion, "
        "cheerful mood, detailed environment, "
        "{scene}. No text, no watermarks."
    ),
    "유화-클래식": (
        "A classic oil painting on canvas, impressionist style, "
        "thick visible brushstrokes, rich warm color palette, "
        "museum quality fine art, dramatic chiaroscuro lighting, "
        "{scene}. No text, no signatures."
    ),
    "미니멀-모던": (
        "A clean modern minimalist design, flat illustration style, "
        "limited color palette, geometric shapes, "
        "professional graphic design, editorial quality, "
        "{scene}. No text, no watermarks."
    ),
    "키워드만": (
        "{scene}, cinematic, photorealistic, 4K, vibrant colors, "
        "no text, no watermark, no logo"
    ),
}

# ============================================================
# 모델 옵션
# ============================================================
MODELS = {
    "Pollinations - Flux": {
        "provider": "pollinations",
        "model": "flux",
        "params": "enhance=true&nologo=true",
    },
    "Pollinations - Flux (no enhance)": {
        "provider": "pollinations",
        "model": "flux",
        "params": "nologo=true",
    },
    "Pollinations - Turbo": {
        "provider": "pollinations",
        "model": "turbo",
        "params": "enhance=true&nologo=true",
    },
    "Pollinations - GPT Image": {
        "provider": "pollinations",
        "model": "gptimage",
        "params": "enhance=true&nologo=true",
    },
    "Pollinations - Seedream": {
        "provider": "pollinations",
        "model": "seedream",
        "params": "enhance=true&nologo=true",
    },
    "Gemini Image (API키 필요)": {
        "provider": "gemini",
        "model": "gemini-2.5-flash-image",
    },
}

# ============================================================
# 테스트 장면
# ============================================================
TEST_SCENES = [
    "Cherry blossom trees in full bloom along a river in Seoul, Korea during spring, petals floating in the wind",
    "A vibrant green rice paddy field in Korean countryside during summer with mountains in the background",
    "Colorful autumn foliage covering the mountains of Naejangsan National Park in Korea",
    "A snowy traditional Korean hanok village in winter with smoke rising from chimneys",
    "A bustling Korean traditional market with colorful lanterns and street food vendors",
]


class ImageTester:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("yFriend 이미지 품질 비교 테스터")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e1e")

        self.results = []  # [(label, pil_image, info_text), ...]
        self.photo_refs = []  # prevent GC

        self._build_ui()

    def _build_ui(self):
        # 상단 컨트롤
        ctrl = tk.Frame(self.root, bg="#2d2d2d", padx=10, pady=8)
        ctrl.pack(fill=tk.X)

        # 장면 선택
        tk.Label(ctrl, text="장면:", bg="#2d2d2d", fg="white", font=("맑은 고딕", 10)).pack(side=tk.LEFT)
        self.scene_var = tk.StringVar()
        self.scene_combo = ttk.Combobox(ctrl, textvariable=self.scene_var, width=80, state="readonly")
        self.scene_combo["values"] = TEST_SCENES
        self.scene_combo.current(0)
        self.scene_combo.pack(side=tk.LEFT, padx=(5, 15))

        # 커스텀 장면 입력
        tk.Label(ctrl, text="직접입력:", bg="#2d2d2d", fg="white", font=("맑은 고딕", 10)).pack(side=tk.LEFT)
        self.custom_scene = tk.Entry(ctrl, width=50, font=("맑은 고딕", 10))
        self.custom_scene.pack(side=tk.LEFT, padx=(5, 15))

        # 두번째 줄
        ctrl2 = tk.Frame(self.root, bg="#2d2d2d", padx=10, pady=5)
        ctrl2.pack(fill=tk.X)

        # 프리셋 선택
        tk.Label(ctrl2, text="프리셋:", bg="#2d2d2d", fg="white", font=("맑은 고딕", 10)).pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value="실사-시네마틱")
        self.preset_combo = ttk.Combobox(ctrl2, textvariable=self.preset_var, width=20, state="readonly")
        self.preset_combo["values"] = list(PRESETS.keys())
        self.preset_combo.pack(side=tk.LEFT, padx=(5, 15))

        # 모델 선택
        tk.Label(ctrl2, text="모델:", bg="#2d2d2d", fg="white", font=("맑은 고딕", 10)).pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value="Pollinations - Flux")
        self.model_combo = ttk.Combobox(ctrl2, textvariable=self.model_var, width=30, state="readonly")
        self.model_combo["values"] = list(MODELS.keys())
        self.model_combo.pack(side=tk.LEFT, padx=(5, 15))

        # 버튼
        self.gen_btn = tk.Button(
            ctrl2, text="1장 생성", command=self._generate_one,
            bg="#0078d4", fg="white", font=("맑은 고딕", 10, "bold"),
            padx=15, pady=3
        )
        self.gen_btn.pack(side=tk.LEFT, padx=5)

        self.compare_btn = tk.Button(
            ctrl2, text="전체 프리셋 비교", command=self._compare_all_presets,
            bg="#107c10", fg="white", font=("맑은 고딕", 10, "bold"),
            padx=15, pady=3
        )
        self.compare_btn.pack(side=tk.LEFT, padx=5)

        self.model_btn = tk.Button(
            ctrl2, text="전체 모델 비교", command=self._compare_all_models,
            bg="#d83b01", fg="white", font=("맑은 고딕", 10, "bold"),
            padx=15, pady=3
        )
        self.model_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = tk.Button(
            ctrl2, text="초기화", command=self._clear,
            bg="#555", fg="white", font=("맑은 고딕", 10),
            padx=10, pady=3
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # 프롬프트 미리보기
        prompt_frame = tk.Frame(self.root, bg="#1e1e1e", padx=10, pady=3)
        prompt_frame.pack(fill=tk.X)
        tk.Label(prompt_frame, text="프롬프트 미리보기:", bg="#1e1e1e", fg="#aaa",
                 font=("맑은 고딕", 9)).pack(side=tk.LEFT)
        self.prompt_preview = tk.Label(
            prompt_frame, text="", bg="#1e1e1e", fg="#ccc",
            font=("맑은 고딕", 9), anchor="w", wraplength=1300
        )
        self.prompt_preview.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.preset_combo.bind("<<ComboboxSelected>>", self._update_preview)
        self.scene_combo.bind("<<ComboboxSelected>>", self._update_preview)
        self._update_preview()

        # 이미지 표시 영역 (스크롤)
        canvas_frame = tk.Frame(self.root, bg="#1e1e1e")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar_y = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar_x = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.image_frame = tk.Frame(self.canvas, bg="#1e1e1e")
        self.canvas.create_window((0, 0), window=self.image_frame, anchor="nw")
        self.image_frame.bind("<Configure>",
                              lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # 상태바
        self.status = tk.Label(
            self.root, text="준비", bg="#007acc", fg="white",
            font=("맑은 고딕", 10), anchor="w", padx=10
        )
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def _get_scene(self):
        custom = self.custom_scene.get().strip()
        return custom if custom else self.scene_var.get()

    def _build_full_prompt(self, preset_name, scene):
        template = PRESETS[preset_name]
        return template.format(scene=scene)

    def _update_preview(self, event=None):
        scene = self._get_scene()
        preset = self.preset_var.get()
        prompt = self._build_full_prompt(preset, scene)
        self.prompt_preview.config(text=prompt[:200] + "..." if len(prompt) > 200 else prompt)

    def _set_status(self, text):
        self.status.config(text=text)
        self.root.update_idletasks()

    def _set_buttons(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.gen_btn.config(state=state)
        self.compare_btn.config(state=state)
        self.model_btn.config(state=state)

    def _generate_one(self):
        scene = self._get_scene()
        preset = self.preset_var.get()
        model_name = self.model_var.get()
        threading.Thread(target=self._worker_generate,
                         args=(scene, preset, model_name), daemon=True).start()

    def _compare_all_presets(self):
        scene = self._get_scene()
        model_name = self.model_var.get()
        threading.Thread(target=self._worker_compare_presets,
                         args=(scene, model_name), daemon=True).start()

    def _compare_all_models(self):
        scene = self._get_scene()
        preset = self.preset_var.get()
        threading.Thread(target=self._worker_compare_models,
                         args=(scene, preset), daemon=True).start()

    def _worker_generate(self, scene, preset, model_name):
        self.root.after(0, lambda: self._set_buttons(False))
        prompt = self._build_full_prompt(preset, scene)
        model_cfg = MODELS[model_name]
        label = f"{model_name} / {preset}"

        self.root.after(0, lambda: self._set_status(f"생성 중: {label}..."))

        img, info = self._call_api(prompt, model_cfg)
        if img:
            self.root.after(0, lambda: self._add_image(label, img, info))
            self.root.after(0, lambda: self._set_status(f"완료: {label}"))
        else:
            self.root.after(0, lambda: self._set_status(f"실패: {label} - {info}"))

        self.root.after(0, lambda: self._set_buttons(True))

    def _worker_compare_presets(self, scene, model_name):
        self.root.after(0, lambda: self._set_buttons(False))
        model_cfg = MODELS[model_name]
        total = len(PRESETS)

        for i, (preset_name, _) in enumerate(PRESETS.items()):
            prompt = self._build_full_prompt(preset_name, scene)
            label = f"{model_name} / {preset_name}"
            self.root.after(0, lambda l=label, n=i: self._set_status(
                f"[{n+1}/{total}] 생성 중: {l}..."))

            img, info = self._call_api(prompt, model_cfg)
            if img:
                self.root.after(0, lambda l=label, im=img, inf=info: self._add_image(l, im, inf))

            # Rate limit
            if i < total - 1:
                self.root.after(0, lambda n=i: self._set_status(
                    f"[{n+1}/{total}] 완료. 16초 대기..."))
                time.sleep(16)

        self.root.after(0, lambda: self._set_status(f"전체 프리셋 비교 완료 ({total}장)"))
        self.root.after(0, lambda: self._set_buttons(True))

    def _worker_compare_models(self, scene, preset):
        self.root.after(0, lambda: self._set_buttons(False))
        prompt = self._build_full_prompt(preset, scene)
        poll_models = {k: v for k, v in MODELS.items() if v["provider"] == "pollinations"}
        total = len(poll_models)

        for i, (model_name, model_cfg) in enumerate(poll_models.items()):
            label = f"{model_name} / {preset}"
            self.root.after(0, lambda l=label, n=i: self._set_status(
                f"[{n+1}/{total}] 생성 중: {l}..."))

            img, info = self._call_api(prompt, model_cfg)
            if img:
                self.root.after(0, lambda l=label, im=img, inf=info: self._add_image(l, im, inf))

            if i < total - 1:
                self.root.after(0, lambda n=i: self._set_status(
                    f"[{n+1}/{total}] 완료. 16초 대기..."))
                time.sleep(16)

        self.root.after(0, lambda: self._set_status(f"전체 모델 비교 완료 ({total}장)"))
        self.root.after(0, lambda: self._set_buttons(True))

    def _call_api(self, prompt, model_cfg):
        provider = model_cfg["provider"]

        if provider == "pollinations":
            return self._call_pollinations(prompt, model_cfg)
        elif provider == "gemini":
            return self._call_gemini(prompt, model_cfg)
        return None, "알 수 없는 provider"

    def _call_pollinations(self, prompt, cfg):
        try:
            encoded = quote(prompt)
            model = cfg.get("model", "flux")
            params = cfg.get("params", "")
            url = (
                f"https://image.pollinations.ai/prompt/{encoded}"
                f"?width=1920&height=1080&model={model}&{params}"
            )

            t0 = time.time()
            resp = requests.get(url, timeout=180)
            elapsed = time.time() - t0

            if resp.status_code == 200 and len(resp.content) > 1000:
                img = Image.open(io.BytesIO(resp.content))
                info = f"모델: {model} | 크기: {img.size} | {len(resp.content)//1024}KB | {elapsed:.1f}초"
                return img, info
            else:
                return None, f"status={resp.status_code}, size={len(resp.content)}"
        except Exception as e:
            return None, str(e)[:100]

    def _call_gemini(self, prompt, cfg):
        try:
            import yaml
            config = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))
            keys = config.get("api_keys", {}).get("gemini", [])
            if isinstance(keys, str):
                keys = [keys]

            from google import genai
            from google.genai import types

            for key in keys:
                try:
                    client = genai.Client(api_key=key)
                    t0 = time.time()
                    response = client.models.generate_content(
                        model=cfg["model"],
                        contents=[prompt],
                        config=types.GenerateContentConfig(
                            response_modalities=["TEXT", "IMAGE"],
                        ),
                    )
                    elapsed = time.time() - t0
                    for part in response.candidates[0].content.parts:
                        if part.inline_data is not None:
                            data = part.inline_data.data
                            if isinstance(data, str):
                                import base64
                                data = base64.b64decode(data)
                            img = Image.open(io.BytesIO(data))
                            info = f"Gemini | 크기: {img.size} | {len(data)//1024}KB | {elapsed:.1f}초"
                            return img, info
                except Exception as e:
                    if "429" in str(e):
                        continue
                    return None, str(e)[:100]
            return None, "모든 Gemini 키 실패"
        except Exception as e:
            return None, str(e)[:100]

    def _add_image(self, label, pil_image, info):
        """이미지를 그리드에 추가"""
        idx = len(self.results)
        col = idx % 3
        row = idx // 3

        frame = tk.Frame(self.image_frame, bg="#333", padx=5, pady=5, relief=tk.RAISED, bd=1)
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        # 라벨
        tk.Label(frame, text=label, bg="#333", fg="#00d4ff",
                 font=("맑은 고딕", 9, "bold"), wraplength=400).pack(pady=(3, 2))

        # 이미지 리사이즈
        display_w = 420
        ratio = display_w / pil_image.width
        display_h = int(pil_image.height * ratio)
        resized = pil_image.resize((display_w, display_h), Image.LANCZOS)

        photo = ImageTk.PhotoImage(resized)
        self.photo_refs.append(photo)

        img_label = tk.Label(frame, image=photo, bg="#333")
        img_label.pack()

        # 정보
        tk.Label(frame, text=info, bg="#333", fg="#aaa",
                 font=("맑은 고딕", 8), wraplength=400).pack(pady=(2, 3))

        self.results.append((label, pil_image, info))
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _clear(self):
        self.results.clear()
        self.photo_refs.clear()
        for widget in self.image_frame.winfo_children():
            widget.destroy()
        self._set_status("초기화 완료")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    # PIL 필요
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("Pillow 설치 필요: pip install Pillow")
        exit(1)
    app = ImageTester()
    app.run()
