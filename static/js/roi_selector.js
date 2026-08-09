/**
 * initRoiSelector({ frameId, imgId, boxId, statusId, xId, yId, wId, hId })
 *
 * Lets the operator drag a rectangle over an <img> to select a region
 * of interest, entirely in the browser. Writes the selected box back
 * in the IMAGE'S NATURAL PIXEL COORDINATES (not on-screen CSS pixels)
 * into the given hidden <input> ids, so the server can crop the
 * original full-resolution file correctly regardless of how large the
 * preview was rendered.
 */
function initRoiSelector(opts) {
  const frame = document.getElementById(opts.frameId);
  const img = document.getElementById(opts.imgId);
  const box = document.getElementById(opts.boxId);
  const status = document.getElementById(opts.statusId);
  const xInput = document.getElementById(opts.xId);
  const yInput = document.getElementById(opts.yId);
  const wInput = document.getElementById(opts.wId);
  const hInput = document.getElementById(opts.hId);

  if (!frame || !img) return;

  let dragging = false;
  let startX = 0;
  let startY = 0;

  function scaleFactor() {
    return {
      sx: img.naturalWidth / img.clientWidth,
      sy: img.naturalHeight / img.clientHeight,
    };
  }

  function pointFromEvent(e) {
    const rect = frame.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: Math.max(0, Math.min(clientX - rect.left, rect.width)),
      y: Math.max(0, Math.min(clientY - rect.top, rect.height)),
    };
  }

  function updateBoxVisual(x1, y1, x2, y2) {
    const left = Math.min(x1, x2);
    const top = Math.min(y1, y2);
    const w = Math.abs(x2 - x1);
    const h = Math.abs(y2 - y1);
    box.style.left = left + "px";
    box.style.top = top + "px";
    box.style.width = w + "px";
    box.style.height = h + "px";
    box.classList.remove("hidden");
  }

  function commitSelection(x1, y1, x2, y2) {
    const { sx, sy } = scaleFactor();
    const left = Math.min(x1, x2) * sx;
    const top = Math.min(y1, y2) * sy;
    const w = Math.abs(x2 - x1) * sx;
    const h = Math.abs(y2 - y1) * sy;

    // Hidden inputs are optional — some callers (like live_quality.js)
    // read the box's on-screen geometry directly instead.
    if (xInput) xInput.value = Math.round(left);
    if (yInput) yInput.value = Math.round(top);
    if (wInput) wInput.value = Math.round(w);
    if (hInput) hInput.value = Math.round(h);

    if (w < 4 || h < 4) {
      status.textContent = "Region too small — draw a larger box.";
      status.classList.remove("ready");
      return;
    }
    status.textContent = `Region selected: ${Math.round(w)}×${Math.round(h)} px`;
    status.classList.add("ready");
  }

  function onDown(e) {
    dragging = true;
    const p = pointFromEvent(e);
    startX = p.x;
    startY = p.y;
    updateBoxVisual(startX, startY, startX, startY);
    e.preventDefault();
  }

  function onMove(e) {
    if (!dragging) return;
    const p = pointFromEvent(e);
    updateBoxVisual(startX, startY, p.x, p.y);
    e.preventDefault();
  }

  function onUp(e) {
    if (!dragging) return;
    dragging = false;
    const p = pointFromEvent(e);
    commitSelection(startX, startY, p.x, p.y);
  }

  frame.addEventListener("mousedown", onDown);
  frame.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);

  frame.addEventListener("touchstart", onDown, { passive: false });
  frame.addEventListener("touchmove", onMove, { passive: false });
  window.addEventListener("touchend", onUp);
}
