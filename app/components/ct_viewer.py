"""CT DICOM 3-plane 뷰어 컴포넌트 (Axial / Sagittal / Coronal)"""

from io import BytesIO
from typing import Tuple

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from core.ct_volume import get_axial_slice, get_coronal_slice, get_sagittal_slice
from core.image_processor import apply_windowing, get_window_presets


def render_ct_viewer(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
) -> None:
    """CT 3-plane 뷰어 렌더링 (W/L, Preset, 슬라이스 슬라이더 포함)"""

    n_z, n_y, n_x = volume.shape
    presets = get_window_presets()
    pmin = float(volume.min())
    pmax = float(volume.max())

    # 레이아웃: 컨트롤(좌) | 뷰어(우)
    ctrl_col, view_col = st.columns([1, 3])

    with ctrl_col:
        st.markdown("### Window Settings")

        preset = st.selectbox("Preset", list(presets.keys()), key="ct_preset")
        default_wc, default_ww = presets[preset]

        wc = st.slider(
            "Window Center",
            min_value=int(pmin),
            max_value=int(pmax),
            value=int(np.clip(default_wc, pmin, pmax)),
            key="ct_wc",
        )
        ww = st.slider(
            "Window Width",
            min_value=1,
            max_value=max(1, int(pmax - pmin)),
            value=int(np.clip(default_ww, 1, pmax - pmin)),
            key="ct_ww",
        )

        st.markdown("---")
        st.markdown("### Slice Navigation")

        axial_idx = st.slider(
            "Axial (Z)", 0, n_z - 1, n_z // 2, key="ct_axial"
        )
        sagittal_idx = st.slider(
            "Sagittal (X)", 0, n_x - 1, n_x // 2, key="ct_sagittal"
        )
        coronal_idx = st.slider(
            "Coronal (Y)", 0, n_y - 1, n_y // 2, key="ct_coronal"
        )

        st.markdown("---")
        st.markdown("### Volume Info")
        st.markdown(f"**Dimensions**: {n_x} × {n_y} × {n_z}")
        st.markdown(
            f"**Spacing**: {spacing[2]:.2f} × {spacing[1]:.2f} × {spacing[0]:.2f} mm"
        )
        st.markdown(f"**HU range**: [{int(pmin)}, {int(pmax)}]")

    with view_col:
        # 슬라이스 추출
        axial_raw = get_axial_slice(volume, axial_idx)
        sagittal_raw = get_sagittal_slice(volume, sagittal_idx)
        coronal_raw = get_coronal_slice(volume, coronal_idx)

        # W/L 적용
        axial_w = apply_windowing(axial_raw, wc, ww)
        sagittal_w = apply_windowing(sagittal_raw, wc, ww)
        coronal_w = apply_windowing(coronal_raw, wc, ww)

        # 시상면/관상면: 위아래 반전 (해부학적 방향)
        sagittal_disp = np.flipud(sagittal_w)
        coronal_disp = np.flipud(coronal_w)

        titles = [
            f"Axial  Z={axial_idx}/{n_z-1}",
            f"Sagittal  X={sagittal_idx}/{n_x-1}",
            f"Coronal  Y={coronal_idx}/{n_y-1}",
        ]
        images = [axial_w, sagittal_disp, coronal_disp]

        # Crosshair 좌표 (flipud 적용 후 기준)
        # Axial:    수평=coronal_idx, 수직=sagittal_idx
        # Sagittal: 수평=(n_z-1-axial_idx), 수직=coronal_idx
        # Coronal:  수평=(n_z-1-axial_idx), 수직=sagittal_idx
        crosshairs = [
            (coronal_idx, sagittal_idx),
            (n_z - 1 - axial_idx, coronal_idx),
            (n_z - 1 - axial_idx, sagittal_idx),
        ]
        line_colors = [("yellow", "cyan"), ("red", "yellow"), ("red", "cyan")]

        fig = plt.figure(figsize=(15, 5), facecolor="black")
        gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.04, hspace=0)

        for i, (title, img, (ch_y, ch_x), (h_col, v_col)) in enumerate(
            zip(titles, images, crosshairs, line_colors)
        ):
            ax = fig.add_subplot(gs[i])
            ax.imshow(img, cmap="gray", aspect="auto", interpolation="bilinear")
            ax.set_title(title, color="white", fontsize=9, pad=2)
            ax.axis("off")

            # Crosshair
            ax.axhline(y=ch_y, color=h_col, linewidth=0.8, alpha=0.7)
            ax.axvline(x=ch_x, color=v_col, linewidth=0.8, alpha=0.7)

        plt.tight_layout(pad=0.3)

        # PNG bytes로 저장 (렌더 1회, 표시 + LLM 공유 모두 사용)
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="black")
        plt.close(fig)
        buf.seek(0)
        img_bytes = buf.getvalue()

        st.image(img_bytes, use_column_width=True)
        st.session_state.current_image_bytes = img_bytes
