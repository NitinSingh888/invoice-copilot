/* Invoice Copilot — line icon set. Attaches window.Icon (a small map of components). */
(function () {
  const S = ({ d, fill, ...p }) => {
    const kids = Array.isArray(d) ? d.map((c, i) => React.cloneElement(c, { key: i })) : d;
    return React.createElement("svg", { viewBox: "0 0 24 24", fill: fill || "none", stroke: "currentColor",
      strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", ...p }, kids);
  };
  const P = (s) => React.createElement("path", { d: s });
  const L = (x1, y1, x2, y2) => React.createElement("line", { x1, y1, x2, y2 });
  const C = (cx, cy, r) => React.createElement("circle", { cx, cy, r });

  const Icon = {
    check:    (p) => S({ ...p, d: P("M20 6 9 17l-5-5") }),
    clock:    (p) => S({ ...p, d: [C(12, 12, 9), P("M12 7v5l3 2")] }),
    alert:    (p) => S({ ...p, d: [P("M10.3 3.7 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z"), L(12, 9, 12, 13), L(12, 17, 12, 17)] }),
    shield:   (p) => S({ ...p, d: [P("M12 2 4 5v6c0 5 3.5 8 8 11 4.5-3 8-6 8-11V5l-8-3Z"), P("m9 12 2 2 4-4")] }),
    shieldX:  (p) => S({ ...p, d: [P("M12 2 4 5v6c0 5 3.5 8 8 11 4.5-3 8-6 8-11V5l-8-3Z"), L(9.5, 9.5, 14.5, 14.5), L(14.5, 9.5, 9.5, 14.5)] }),
    file:     (p) => S({ ...p, d: [P("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"), P("M14 2v6h6"), L(9, 13, 15, 13), L(9, 17, 13, 17)] }),
    arrowR:   (p) => S({ ...p, d: [L(5, 12, 19, 12), P("m13 6 6 6-6 6")] }),
    send:     (p) => S({ ...p, d: [P("M22 2 11 13"), P("M22 2l-7 20-4-9-9-4 20-7Z")] }),
    x:        (p) => S({ ...p, d: [L(18, 6, 6, 18), L(6, 6, 18, 18)] }),
    sun:      (p) => S({ ...p, d: [C(12, 12, 4), L(12, 2, 12, 4), L(12, 20, 12, 22), L(4.2, 4.2, 5.6, 5.6), L(18.4, 18.4, 19.8, 19.8), L(2, 12, 4, 12), L(20, 12, 22, 12), L(4.2, 19.8, 5.6, 18.4), L(18.4, 5.6, 19.8, 4.2)] }),
    moon:     (p) => S({ ...p, d: P("M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z") }),
    sliders:  (p) => S({ ...p, d: [L(4, 21, 4, 14), L(4, 10, 4, 3), L(12, 21, 12, 12), L(12, 8, 12, 3), L(20, 21, 20, 16), L(20, 12, 20, 3), L(1, 14, 7, 14), L(9, 8, 15, 8), L(17, 16, 23, 16)] }),
    play:     (p) => S({ ...p, fill: "currentColor", stroke: "none", d: P("M8 5v14l11-7z") }),
    pause:    (p) => S({ ...p, fill: "currentColor", stroke: "none", d: [React.createElement("rect", { x: 6, y: 5, width: 4, height: 14, rx: 1 }), React.createElement("rect", { x: 14, y: 5, width: 4, height: 14, rx: 1 })] }),
    spark:    (p) => S({ ...p, d: P("M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z") }),
    spark2:   (p) => S({ ...p, fill: "currentColor", stroke: "none", d: [P("M12 2l1.6 4.8L18 8l-4.4 1.2L12 14l-1.6-4.8L6 8l4.4-1.2L12 2Z"), P("M19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14Z")] }),
    route:    (p) => S({ ...p, d: [C(6, 19, 2.5), C(18, 5, 2.5), P("M8.5 19H15a3 3 0 0 0 3-3V7.5"), P("M15.5 5H9a3 3 0 0 0-3 3v8.5")] }),
    gavel:    (p) => S({ ...p, d: [P("m14 13-7.5 7.5a2.1 2.1 0 0 1-3-3L11 10"), P("m16 16 6-6"), P("m8 8 6-6"), P("m9 7 4 4"), P("m17 11 4 4"), L(3, 21, 12, 21)] }),
    branch:   (p) => S({ ...p, d: [L(6, 3, 6, 15), C(18, 6, 3), C(6, 18, 3), P("M18 9a9 9 0 0 1-9 9")] }),
    book:     (p) => S({ ...p, d: [P("M4 19.5A2.5 2.5 0 0 1 6.5 17H20"), P("M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z")] }),
    pencil:   (p) => S({ ...p, d: [P("M17 3a2.1 2.1 0 0 1 3 3L7.5 18.5 3 20l1.5-4.5L17 3Z")] }),
    eye:      (p) => S({ ...p, d: [P("M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"), C(12, 12, 3)] }),
    dollar:   (p) => S({ ...p, d: [L(12, 2, 12, 22), P("M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6")] }),
    lock:     (p) => S({ ...p, d: [React.createElement("rect", { x: 4, y: 11, width: 16, height: 10, rx: 2 }), P("M8 11V7a4 4 0 0 1 8 0v4")] }),
    plus:     (p) => S({ ...p, d: [L(12, 5, 12, 19), L(5, 12, 19, 12)] }),
    minus:    (p) => S({ ...p, d: L(5, 12, 19, 12) }),
    chevU:    (p) => S({ ...p, d: P("m6 15 6-6 6 6") }),
    chevD:    (p) => S({ ...p, d: P("m6 9 6 6 6-6") }),
    scale:    (p) => S({ ...p, d: [P("M12 3v18"), P("M7 7h10"), P("m7 7-3 6a3 3 0 0 0 6 0L7 7Z"), P("m17 7-3 6a3 3 0 0 0 6 0l-3-6Z"), L(8, 21, 16, 21)] }),
    link:     (p) => S({ ...p, d: [P("M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1.5 1.5"), P("M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1.5-1.5")] }),
    inbox:    (p) => S({ ...p, d: [P("M22 12h-6l-2 3h-4l-2-3H2"), P("M5.5 5.5 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.5A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.5Z")] }),
    bolt:     (p) => S({ ...p, fill: "currentColor", stroke: "none", d: P("M13 2 4.5 13.5H11l-1 8.5 8.5-11.5H12l1-8.5Z") }),
    user:     (p) => S({ ...p, d: [C(12, 8, 4), P("M4 21a8 8 0 0 1 16 0")] }),
    hold:     (p) => S({ ...p, d: [C(12, 12, 9), L(9.5, 9.5, 9.5, 14.5), L(14.5, 9.5, 14.5, 14.5)] }),
    search:   (p) => S({ ...p, d: [C(11, 11, 7), L(21, 21, 16.5, 16.5)] }),
    chart:    (p) => S({ ...p, d: [P("M3 3v18h18"), P("M7 14l3-3 3 3 4-5")] }),
  };
  window.Icon = Icon;
})();
