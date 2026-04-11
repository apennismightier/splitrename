"""
naming_dialog.py — FileBot-style episode naming dialog for SplitRename.

Opens when the user clicks "Episode Names (TMDB/TVDB)".
Lets the user search for a show, pick the right result, review the
episode-to-file mapping, and confirm before splitting begins.
"""

from __future__ import annotations
import re
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QComboBox, QGroupBox, QSplitter,
    QFrame, QMessageBox, QHeaderView, QCheckBox, QSpinBox,
    QTabWidget, QWidget, QProgressBar, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

from episode_namer import (
    TMDBClient, TVDBClient, ShowResult, EpisodeInfo,
    NamingPlan, build_output_names, guess_season_episode, safe_filename
)


# ─────────────────────────────────────────────
# SEARCH WORKER
# ─────────────────────────────────────────────

class SearchWorker(QThread):
    results  = pyqtSignal(list)   # list[ShowResult]
    error    = pyqtSignal(str)

    def __init__(self, query: str, year: str,
                 tmdb_key: str, tvdb_key: str):
        super().__init__()
        self.query    = query
        self.year     = year
        self.tmdb_key = tmdb_key
        self.tvdb_key = tvdb_key

    def run(self):
        all_results: list[ShowResult] = []
        # TMDB first (no key needed for search)
        try:
            client = TMDBClient(self.tmdb_key)
            all_results += client.search_show(self.query, self.year)
        except Exception as e:
            pass   # surface TVDB results instead

        # TVDB if key is provided
        if self.tvdb_key:
            try:
                client = TVDBClient(self.tvdb_key)
                tvdb_r = client.search_show(self.query, self.year)
                # Merge — avoid duplicates by name+year
                existing = {(r.name.lower(), r.year) for r in all_results}
                for r in tvdb_r:
                    if (r.name.lower(), r.year) not in existing:
                        all_results.append(r)
                        existing.add((r.name.lower(), r.year))
            except Exception:
                pass

        if all_results:
            self.results.emit(all_results)
        else:
            self.error.emit(
                "No results found. Check spelling or try a different year.\n\n"
                "Tip: For TMDB episode details, a free API key is required.\n"
                "Get one at themoviedb.org/settings/api"
            )


class EpisodeFetchWorker(QThread):
    episodes = pyqtSignal(dict)   # {season: [EpisodeInfo]}
    error    = pyqtSignal(str)

    def __init__(self, show: ShowResult, tmdb_key: str, tvdb_key: str):
        super().__init__()
        self.show     = show
        self.tmdb_key = tmdb_key
        self.tvdb_key = tvdb_key

    def run(self):
        try:
            if self.show.source == "tmdb":
                client = TMDBClient(self.tmdb_key)
                seasons = client.get_all_episodes(self.show.id)
            else:
                client = TVDBClient(self.tvdb_key)
                # Fetch seasons 1-20, stop on first empty
                seasons: dict[int, list[EpisodeInfo]] = {}
                for s in range(1, 21):
                    try:
                        eps = client.get_episodes(self.show.id, s)
                        if not eps:
                            break
                        seasons[s] = eps
                    except Exception:
                        break
            self.episodes.emit(seasons)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────
# MAIN DIALOG
# ─────────────────────────────────────────────

class EpisodeNamingDialog(QDialog):
    """
    FileBot-style dialog.
    Left pane:   search + show results
    Right pane:  file-to-episode mapping table
    Bottom:      confirm / cancel
    """

    # Emitted when user confirms — list of NamingPlan (one per job)
    confirmed = pyqtSignal(list)

    def __init__(self, jobs: list, settings: dict, parent=None):
        super().__init__(parent)
        self.jobs     = jobs       # list of VideoJob
        self.settings = settings   # app settings dict (for output ext)
        self.tmdb_key = settings.get("tmdb_api_key", "") or "181eaf5e7326b9d157a652d0e591087e"
        self.tvdb_key = settings.get("tvdb_api_key", "") or "3bc3f1c3-058b-4b42-9949-466b4f7aba20"

        self._show_results:  list[ShowResult]              = []
        self._selected_show: Optional[ShowResult]          = None
        self._all_episodes:  dict[int, list[EpisodeInfo]]  = {}
        self._plans:         list[NamingPlan]              = []

        self.setWindowTitle("Episode Naming — TMDB / TVDB")
        self.setMinimumSize(1100, 680)
        self.resize(1200, 720)
        self._apply_styles()
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        title_bar = QFrame(); title_bar.setObjectName("namingHeader")
        title_bar.setFixedHeight(48)
        tl = QHBoxLayout(title_bar); tl.setContentsMargins(20, 0, 20, 0)
        t = QLabel("EPISODE NAMING"); t.setObjectName("namingTitle")
        tl.addWidget(t)
        tl.addStretch()
        sub = QLabel("Powered by TMDB + TVDB"); sub.setObjectName("namingSub")
        tl.addWidget(sub)
        root.addWidget(title_bar)

        # API key bar
        # Main splitter: left = search, right = mapping
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_search_panel())
        splitter.addWidget(self._build_mapping_panel())
        splitter.setSizes([380, 720])
        root.addWidget(splitter, stretch=1)

        # Bottom button bar
        root.addWidget(self._build_bottom_bar())

    def _build_search_panel(self):
        panel = QFrame(); panel.setObjectName("searchPanel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(8)

        # Search bar
        sg = QGroupBox("Search Show"); sg.setObjectName("settingsGroup")
        sl = QVBoxLayout(sg); sl.setSpacing(6)

        q_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("timeInput")
        self.search_edit.setPlaceholderText("Show name, e.g. Curious George")
        self.search_edit.returnPressed.connect(self._do_search)
        q_row.addWidget(self.search_edit)

        yr_lbl = QLabel("Year:")
        self.year_edit = QLineEdit(); self.year_edit.setFixedWidth(55)
        self.year_edit.setObjectName("timeInput"); self.year_edit.setPlaceholderText("opt.")
        q_row.addWidget(yr_lbl); q_row.addWidget(self.year_edit)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("primaryBtn")
        self.search_btn.clicked.connect(self._do_search)
        q_row.addWidget(self.search_btn)
        sl.addLayout(q_row)

        self.search_status = QLabel("Enter a show name and click Search")
        self.search_status.setObjectName("searchStatus")
        sl.addWidget(self.search_status)

        lay.addWidget(sg)

        # Results list
        rg = QGroupBox("Results"); rg.setObjectName("settingsGroup")
        rl = QVBoxLayout(rg); rl.setSpacing(4)
        self.results_list = QListWidget()
        self.results_list.setObjectName("resultsList")
        self.results_list.currentRowChanged.connect(self._on_show_selected)
        rl.addWidget(self.results_list)
        lay.addWidget(rg, stretch=1)

        # Season picker
        sp_row = QHBoxLayout()
        sp_row.addWidget(QLabel("Season:"))
        self.season_spin = QSpinBox()
        self.season_spin.setObjectName("spinBox"); self.season_spin.setRange(1, 50)
        self.season_spin.setValue(1)
        self.season_spin.valueChanged.connect(self._rebuild_mapping)
        sp_row.addWidget(self.season_spin); sp_row.addStretch()

        load_btn = QPushButton("Load Episodes")
        load_btn.setObjectName("smallBtn")
        load_btn.clicked.connect(self._load_episodes)
        sp_row.addWidget(load_btn)
        lay.addLayout(sp_row)

        # Auto-detect from filenames
        auto_btn = QPushButton("Auto-detect show from filenames")
        auto_btn.setObjectName("smallBtnGhost")
        auto_btn.setToolTip("Parses S##E## from filenames to pre-fill the search")
        auto_btn.clicked.connect(self._auto_detect)
        lay.addWidget(auto_btn)

        return panel

    def _build_mapping_panel(self):
        panel = QFrame(); panel.setObjectName("mappingPanel")
        lay = QVBoxLayout(panel); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(8)

        # Options row
        opt_row = QHBoxLayout()
        self.include_show_cb = QCheckBox("Include show name in filename")
        self.include_show_cb.setChecked(True)
        self.include_show_cb.stateChanged.connect(self._rebuild_mapping)
        opt_row.addWidget(self.include_show_cb)
        opt_row.addStretch()
        self.ep_offset_lbl = QLabel("Episode offset:")
        self.ep_offset = QSpinBox()
        self.ep_offset.setObjectName("spinBox")
        self.ep_offset.setRange(-50, 200); self.ep_offset.setValue(0)
        self.ep_offset.setToolTip("Shift all episode numbers by this amount")
        self.ep_offset.valueChanged.connect(self._rebuild_mapping)
        opt_row.addWidget(self.ep_offset_lbl); opt_row.addWidget(self.ep_offset)
        lay.addLayout(opt_row)

        # Mapping table
        mg = QGroupBox("File → Episode Mapping"); mg.setObjectName("settingsGroup")
        ml = QVBoxLayout(mg); ml.setSpacing(0)

        self.mapping_table = QTableWidget()
        self.mapping_table.setObjectName("mappingTable")
        self.mapping_table.setColumnCount(4)
        self.mapping_table.setHorizontalHeaderLabels(
            ["Source File", "Episode", "Episode Title", "Output Filename"]
        )
        self.mapping_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.mapping_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.mapping_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.mapping_table.setColumnWidth(1, 80)
        self.mapping_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.mapping_table.setAlternatingRowColors(True)
        self.mapping_table.verticalHeader().setVisible(False)
        ml.addWidget(self.mapping_table)
        lay.addWidget(mg, stretch=1)

        # Status
        self.mapping_status = QLabel("Select a show and load episodes to build the mapping")
        self.mapping_status.setObjectName("searchStatus")
        lay.addWidget(self.mapping_status)

        return panel

    def _build_bottom_bar(self):
        bar = QFrame(); bar.setObjectName("bottomBar"); bar.setFixedHeight(52)
        lay = QHBoxLayout(bar); lay.setContentsMargins(16, 8, 16, 8); lay.setSpacing(10)

        self.progress = QProgressBar()
        self.progress.setObjectName("mainProgress")
        self.progress.setFixedWidth(200); self.progress.setFixedHeight(18)
        self.progress.setTextVisible(False); self.progress.hide()
        lay.addWidget(self.progress)

        lay.addStretch()

        skip_btn = QPushButton("Skip Naming (use filenames)")
        skip_btn.setObjectName("smallBtnGhost")
        skip_btn.clicked.connect(self.reject)
        lay.addWidget(skip_btn)

        self.confirm_btn = QPushButton("✓  Confirm — Use These Names")
        self.confirm_btn.setObjectName("batchBtn")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._confirm)
        lay.addWidget(self.confirm_btn)

        return bar

    # ── SEARCH ────────────────────────────────────────────────────────────────

    def _do_search(self):
        q = self.search_edit.text().strip()
        if not q:
            return
        self.search_btn.setEnabled(False)
        self.search_status.setText("Searching…")
        self.results_list.clear()
        self.progress.show(); self.progress.setRange(0, 0)

        self._worker = SearchWorker(q, self.year_edit.text().strip(),
                                    self.tmdb_key, self.tvdb_key)
        self._worker.results.connect(self._on_search_results)
        self._worker.error.connect(self._on_search_error)
        self._worker.finished.connect(lambda: (
            self.search_btn.setEnabled(True),
            self.progress.hide()
        ))
        self._worker.start()

    def _on_search_results(self, results: list):
        self._show_results = results
        self.results_list.clear()
        for r in results:
            yr  = f" ({r.year})" if r.year else ""
            src = "TMDB" if r.source == "tmdb" else "TVDB"
            item = QListWidgetItem(f"[{src}]  {r.name}{yr}")
            item.setToolTip(r.overview or "No overview available")
            self.results_list.addItem(item)
        self.search_status.setText(f"{len(results)} result(s) found")
        if results:
            self.results_list.setCurrentRow(0)

    def _on_search_error(self, msg: str):
        self.search_status.setText("Search failed")
        QMessageBox.warning(self, "Search Error", msg)

    def _on_show_selected(self, row: int):
        if row < 0 or row >= len(self._show_results):
            return
        self._selected_show = self._show_results[row]

    def _auto_detect(self):
        """Parse S##E## from loaded filenames to pre-fill search."""
        if not self.jobs:
            return
        for job in self.jobs:
            fn = job.filename
            # Try to extract show name from filename (text before S##E##)
            m = re.match(r'^(.*?)[. _-]+[Ss]\d+[Ee]\d+', fn)
            if m:
                raw = m.group(1).replace(".", " ").replace("_", " ").strip()
                self.search_edit.setText(raw)
                # Try to get year from filename
                yr_m = re.search(r'\b(19\d\d|20\d\d)\b', fn)
                if yr_m:
                    self.year_edit.setText(yr_m.group(1))
                # Get season number
                s_m = re.search(r'[Ss](\d+)', fn)
                if s_m:
                    self.season_spin.setValue(int(s_m.group(1)))
                break
        self._do_search()

    # ── EPISODE LOADING ───────────────────────────────────────────────────────


    def _auto_detect_from(self, filename: str):
        """
        Called with the ORIGINAL source filename to extract show name and
        starting episode. The dialog is loaded with OUTPUT files (one per segment).
        Sets the episode offset so output_001 maps to the correct episode.

        e.g. source = "Curious.George.S01E11-E12.mkv"
             → show="Curious George", season=1, first_ep=11, offset=10
        """
        m = re.match(r'^(.*?)[. _-]+[Ss](\d+)[Ee](\d+)', filename)
        if m:
            raw      = m.group(1).replace(".", " ").replace("_", " ").strip()
            season   = int(m.group(2))
            first_ep = int(m.group(3))
            self.search_edit.setText(raw)
            self.season_spin.setValue(season)
            self.ep_offset.setValue(first_ep - 1)
            yr = re.search(r'(19\d\d|20\d\d)', filename)
            if yr:
                self.year_edit.setText(yr.group(1))
            self._do_search()
        else:
            self.search_edit.setFocus()

    def _load_episodes(self):
        if not self._selected_show:
            QMessageBox.information(self, "No Show", "Select a show from the results first.")
            return
        # API keys are hardcoded — no check needed

        self.progress.setRange(0, 0); self.progress.show()
        self.mapping_status.setText("Loading episodes…")
        self.confirm_btn.setEnabled(False)

        self._fetch_worker = EpisodeFetchWorker(
            self._selected_show, self.tmdb_key, self.tvdb_key
        )
        self._fetch_worker.episodes.connect(self._on_episodes_loaded)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.finished.connect(lambda: self.progress.hide())
        self._fetch_worker.start()

    def _on_episodes_loaded(self, all_episodes: dict):
        self._all_episodes = all_episodes
        n_seasons = len(all_episodes)
        n_eps     = sum(len(v) for v in all_episodes.values())
        self.mapping_status.setText(
            f"Loaded {n_eps} episode(s) across {n_seasons} season(s) — "
            f"showing season {self.season_spin.value()}"
        )
        self._rebuild_mapping()

    def _on_fetch_error(self, msg: str):
        self.mapping_status.setText("Failed to load episodes")
        QMessageBox.warning(self, "Episode Load Error", msg)

    # ── MAPPING TABLE ─────────────────────────────────────────────────────────

    def _rebuild_mapping(self):
        if not self._all_episodes or not self._selected_show:
            return

        season  = self.season_spin.value()
        offset  = self.ep_offset.value()
        eps     = self._all_episodes.get(season, [])
        include = self.include_show_cb.isChecked()

        # Determine output extension from settings
        ext_map = {"mp4": ".mp4", "mkv": ".mkv", "source": ""}
        out_ext = ext_map.get(self.settings.get("out_container", "source"), "")

        # Build plans: one NamingPlan per job
        self._plans = []
        all_rows: list[tuple] = []   # (job, segment_idx, ep_info, out_name)

        ep_cursor = 0   # rolling episode index across all jobs

        for job in self.jobs:
            # How many segments will this job produce?
            enabled_splits = [sp for sp in job.split_points if sp.enabled]
            n_segments = len(enabled_splits) + 1

            # What extension to use for this job?
            src_ext = "." + job.filename.rsplit(".", 1)[-1].lower() if "." in job.filename else ".mkv"
            job_ext = out_ext if out_ext else src_ext

            plan_eps: list[EpisodeInfo] = []
            plan_names: list[str] = []

            for seg_i in range(n_segments):
                ep_abs_idx = ep_cursor + offset
                if 0 <= ep_abs_idx < len(eps):
                    ep = eps[ep_abs_idx]
                else:
                    # Synthetic episode placeholder
                    ep = EpisodeInfo(season=season,
                                     episode=ep_cursor + 1 + offset,
                                     title=f"Episode {ep_cursor + 1 + offset}")
                plan_eps.append(ep)

                tag   = f"S{season:02d}E{ep.episode:02d}"
                title = safe_filename(ep.title)
                if include:
                    show  = safe_filename(self._selected_show.name)
                    name  = f"{show} - {tag} - {title}{job_ext}"
                else:
                    name  = f"{tag} - {title}{job_ext}"
                plan_names.append(name)

                all_rows.append((job, seg_i, ep, name))
                ep_cursor += 1

            plan = NamingPlan(
                job_filename=job.filename,
                show_name=self._selected_show.name,
                season=season,
                episodes=plan_eps,
                output_names=plan_names,
                confirmed=False,
            )
            self._plans.append(plan)

        # Populate table
        self.mapping_table.setRowCount(len(all_rows))
        for row_i, (job, seg_i, ep, out_name) in enumerate(all_rows):
            # Source file
            src_text = job.filename if seg_i == 0 else f"  └ segment {seg_i + 1}"
            src_item = QTableWidgetItem(src_text)
            src_item.setFlags(src_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if seg_i == 0:
                src_item.setForeground(QColor("#e6edf3"))
            else:
                src_item.setForeground(QColor("#64748b"))
            self.mapping_table.setItem(row_i, 0, src_item)

            # Episode tag
            tag_item = QTableWidgetItem(f"S{ep.season:02d}E{ep.episode:02d}")
            tag_item.setForeground(QColor("#f97316"))
            tag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(row_i, 1, tag_item)

            # Episode title (editable — user can tweak)
            title_item = QTableWidgetItem(ep.title)
            title_item.setForeground(QColor("#c9d1d9"))
            self.mapping_table.setItem(row_i, 2, title_item)

            # Output filename
            out_item = QTableWidgetItem(out_name)
            out_item.setForeground(QColor("#4ade80"))
            out_item.setFlags(out_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(row_i, 3, out_item)

        self.mapping_table.resizeRowsToContents()
        self.confirm_btn.setEnabled(bool(self._plans))
        self.mapping_status.setText(
            f"✓  {len(all_rows)} segment(s) mapped  —  "
            f"double-click a title cell to edit it"
        )

        # Wire title edits to update output column
        self.mapping_table.cellChanged.connect(self._on_cell_changed)

    def _on_cell_changed(self, row: int, col: int):
        if col != 2:   # only title column
            return
        # Regenerate output filename for this row
        title_item = self.mapping_table.item(row, 2)
        tag_item   = self.mapping_table.item(row, 1)
        out_item   = self.mapping_table.item(row, 3)
        if not all([title_item, tag_item, out_item]):
            return
        tag   = tag_item.text()
        title = safe_filename(title_item.text())
        inc   = self.include_show_cb.isChecked()
        show  = safe_filename(self._selected_show.name) if self._selected_show else ""
        ext   = out_item.text().rsplit(".", 1)[-1] if "." in out_item.text() else "mkv"
        if inc and show:
            new_out = f"{show} - {tag} - {title}.{ext}"
        else:
            new_out = f"{tag} - {title}.{ext}"
        out_item.setText(new_out)

    # ── CONFIRM ───────────────────────────────────────────────────────────────

    def _confirm(self):
        # Read back any user edits from the table
        row_i = 0
        for plan in self._plans:
            for seg_i in range(len(plan.output_names)):
                out_item   = self.mapping_table.item(row_i, 3)
                title_item = self.mapping_table.item(row_i, 2)
                if out_item:
                    plan.output_names[seg_i] = out_item.text()
                if title_item and seg_i < len(plan.episodes):
                    plan.episodes[seg_i].title = title_item.text()
                row_i += 1
            plan.confirmed = True

        self.confirmed.emit(self._plans)
        self.accept()

    # ── STYLES ────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog, QWidget {
                background-color: #0d1117; color: #c9d1d9;
                font-family: 'Consolas', 'Courier New', monospace; font-size: 12px;
            }
            #namingHeader { background-color: #010409; border-bottom: 1px solid #21262d; }
            #namingTitle  { font-size: 16px; font-weight: bold; letter-spacing: 2px; color: #e6edf3; }
            #namingSub    { color: #484f58; font-size: 11px; }
            #apiBar       { background-color: #0a0e14; border-bottom: 1px solid #21262d; }
            #searchPanel  { background-color: #0d1117; border-right: 1px solid #21262d; }
            #mappingPanel { background-color: #0d1117; }
            #bottomBar    { background-color: #010409; border-top: 1px solid #21262d; }

            QGroupBox#settingsGroup {
                border: 1px solid #21262d; border-radius: 4px;
                margin-top: 10px; padding-top: 6px;
                font-size: 11px; color: #8b949e; letter-spacing: 1px;
            }
            QGroupBox#settingsGroup::title {
                subcontrol-origin: margin; left: 8px; padding: 0 4px;
            }

            #resultsList { background-color: #0d1117; border: none; outline: none; }
            #resultsList::item { padding: 7px 8px; border-bottom: 1px solid #161b22; }
            #resultsList::item:selected { background-color: #1c2128; color: #e6edf3; }

            QTableWidget#mappingTable {
                background-color: #0d1117; gridline-color: #21262d;
                border: none; outline: none;
                alternate-background-color: #161b22;
            }
            QTableWidget#mappingTable::item { padding: 6px; }
            QHeaderView::section {
                background-color: #010409; color: #8b949e;
                padding: 6px; border: none; border-bottom: 1px solid #21262d;
                font-size: 11px; letter-spacing: 1px;
            }

            #searchStatus { color: #8b949e; font-size: 11px; padding: 2px 4px; }
            #timeInput {
                background-color: #161b22; border: 1px solid #30363d;
                border-radius: 3px; padding: 4px 6px; color: #e6edf3;
            }
            #timeInput:focus { border-color: #f97316; }

            QPushButton#primaryBtn {
                background-color: #1f6feb; color: white; border: none;
                border-radius: 3px; padding: 5px 14px; font-weight: bold;
            }
            QPushButton#primaryBtn:hover { background-color: #388bfd; }
            QPushButton#batchBtn {
                background-color: #f97316; color: #0d1117; border: none;
                border-radius: 3px; padding: 5px 18px; font-weight: bold;
            }
            QPushButton#batchBtn:hover { background-color: #fb923c; }
            QPushButton#batchBtn:disabled { background-color: #30363d; color: #64748b; }
            QPushButton#smallBtn {
                background-color: #21262d; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 3px; padding: 4px 10px;
            }
            QPushButton#smallBtn:hover { border-color: #8b949e; }
            QPushButton#smallBtnGhost {
                background-color: transparent; color: #8b949e;
                border: 1px solid #30363d; border-radius: 3px; padding: 4px 10px;
            }
            QPushButton#smallBtnGhost:hover { color: #c9d1d9; }

            #spinBox { background-color: #161b22; border: 1px solid #30363d;
                        border-radius: 3px; padding: 3px; color: #e6edf3; }
            QCheckBox { color: #c9d1d9; }
            QCheckBox::indicator:checked { background-color: #f97316; border: none; border-radius: 2px; }

            QProgressBar#mainProgress {
                background-color: #21262d; border: none; border-radius: 3px;
            }
            QProgressBar#mainProgress::chunk { background-color: #f97316; border-radius: 3px; }

            QScrollBar:vertical { background: #0d1117; width: 8px; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 4px; min-height: 20px; }
        """)
