- All source code, comments, commit messages, UI strings, logs, and user-facing messages must be in English.
- Business logis will be at DanceTrackerApp, UI has any logic that it's not UI logic.
  UI communicates with the app using DanceTrackerPort, app comunicate with ui using EnventBus
- Store all generic widgets at ui/widgets/generic_widgets
    - Every context menu use ui/widgets/generic_widgets/context_menu.py as base clase
 