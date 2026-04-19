from __future__ import annotations

import subprocess
from dataclasses import dataclass

from gtp_cli.paths import ConversionPaths


@dataclass(frozen=True)
class ConversionRequest:
    paths: ConversionPaths
    app_name: str = "Guitar Pro 8"
    timeout_seconds: int = 120
    settle_delay: float = 2.0
    save_menu: tuple[str, ...] = ("File", "Export", "GPX...")
    png_menu: tuple[str, ...] = ("File", "Export", "PNG...")
    keep_open: bool = False


DEFAULT_GPX_MENUS: tuple[tuple[str, ...], ...] = (
    ("File", "Export", "GPX..."),
    ("文档", "导出", "GPX..."),
)
DEFAULT_PNG_MENUS: tuple[tuple[str, ...], ...] = (
    ("File", "Export", "PNG..."),
    ("文档", "导出", "PNG..."),
)


def parse_menu_path(value: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in value.split(">") if part.strip())
    if len(parts) < 2:
        raise ValueError(f"Menu path must contain at least two parts, for example File>Save As...: {value}")
    return parts


def run_osascript(script: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["osascript", "-"],
        input=script,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def build_applescript(request: ConversionRequest) -> str:
    app_name = _as_string(request.app_name)
    source = _as_string(str(request.paths.source))
    save_block = _build_save_block(request)
    png_block = _build_png_block(request)
    quit_block = "" if request.keep_open else """
try
    tell application appName to quit saving no
on error
    try
        tell application appName to quit
    end try
end try
"""

    return f"""set appName to {app_name}
set inputPath to {source}
set timeoutSeconds to {request.timeout_seconds}
set settleDelay to {request.settle_delay}

on waitForProcess(appName, timeoutSeconds)
    set startedAt to current date
    tell application "System Events"
        repeat until exists process appName
            if ((current date) - startedAt) > timeoutSeconds then error "Timed out waiting for " & appName
            delay 0.25
        end repeat
    end tell
end waitForProcess

on clickMenuPath(appName, menuPath)
    tell application "System Events"
        tell process appName
            set frontmost to true
            set currentMenu to missing value
            repeat with menuIndex from 1 to count of menuPath
                set menuName to item menuIndex of menuPath as text
                if menuIndex is 1 then
                    click menu bar item menuName of menu bar 1
                    set currentMenu to menu menuName of menu bar item menuName of menu bar 1
                else
                    set targetItem to menu item menuName of currentMenu
                    if menuIndex is (count of menuPath) then
                        click targetItem
                    else
                        click targetItem
                        set currentMenu to menu menuName of targetItem
                    end if
                end if
                delay 0.2
            end repeat
        end tell
    end tell
end clickMenuPath

on menuPathExists(appName, menuPath)
    tell application "System Events"
        if not (exists process appName) then return false
        tell process appName
            if not (exists menu bar 1) then return false
            set currentMenu to missing value
            repeat with menuIndex from 1 to count of menuPath
                set menuName to item menuIndex of menuPath as text
                if menuIndex is 1 then
                    if not (exists menu bar item menuName of menu bar 1) then return false
                    set currentMenu to menu menuName of menu bar item menuName of menu bar 1
                else
                    if not (exists menu item menuName of currentMenu) then return false
                    set targetItem to menu item menuName of currentMenu
                    if menuIndex is not (count of menuPath) then
                        set currentMenu to menu menuName of targetItem
                    end if
                end if
            end repeat
        end tell
    end tell
    return true
end menuPathExists

on clickFirstAvailableMenuPath(appName, menuPaths, timeoutSeconds)
    set startedAt to current date
    repeat
        repeat with candidatePath in menuPaths
            if my menuPathExists(appName, candidatePath) then
                my clickMenuPath(appName, candidatePath)
                return
            end if
        end repeat
        if ((current date) - startedAt) > timeoutSeconds then error "Timed out waiting for menu path"
        delay 0.25
    end repeat
end clickFirstAvailableMenuPath

on clickButtonIfPresent(appName, buttonName)
    tell application "System Events"
        tell process appName
            repeat with candidateWindow in windows
                if exists button buttonName of candidateWindow then
                    click button buttonName of candidateWindow
                    return true
                end if
                if exists sheet 1 of candidateWindow then
                    if exists button buttonName of sheet 1 of candidateWindow then
                        click button buttonName of sheet 1 of candidateWindow
                        return true
                    end if
                end if
            end repeat
        end tell
    end tell
    return false
end clickButtonIfPresent

on clickFirstButtonByName(appName, buttonNames)
    tell application "System Events"
        tell process appName
            repeat with candidateWindow in windows
                repeat with buttonName in buttonNames
                    set buttonText to buttonName as text
                    if exists button buttonText of candidateWindow then
                        click button buttonText of candidateWindow
                        return true
                    end if
                    if exists splitter group 1 of candidateWindow then
                        if exists button buttonText of splitter group 1 of candidateWindow then
                            click button buttonText of splitter group 1 of candidateWindow
                            return true
                        end if
                    end if
                    if exists sheet 1 of candidateWindow then
                        if exists button buttonText of sheet 1 of candidateWindow then
                            click button buttonText of sheet 1 of candidateWindow
                            return true
                        end if
                    end if
                end repeat
            end repeat
        end tell
    end tell
    return false
end clickFirstButtonByName

on waitForSaveWindow(appName, timeoutSeconds)
    set startedAt to current date
    tell application "System Events"
        tell process appName
            repeat until exists window 1
                if ((current date) - startedAt) > timeoutSeconds then error "Timed out waiting for save panel"
                delay 0.25
            end repeat
        end tell
    end tell
end waitForSaveWindow

on goToDirectory(appName, outputDirectory, timeoutSeconds)
    tell application "System Events"
        tell process appName
            set frontmost to true
            keystroke "g" using {{command down, shift down}}
        end tell
    end tell

    set startedAt to current date
    tell application "System Events"
        tell process appName
            repeat until ((exists sheet 1 of window 1) and (exists text field 1 of sheet 1 of window 1))
                if ((current date) - startedAt) > timeoutSeconds then error "Timed out waiting for Go to Folder sheet"
                delay 0.25
            end repeat

            tell sheet 1 of window 1
                set value of text field 1 to outputDirectory
                set focused of text field 1 to true
            end tell
            key code 36

            repeat while exists sheet 1 of window 1
                if ((current date) - startedAt) > timeoutSeconds then error "Timed out navigating to output directory"
                delay 0.25
            end repeat
        end tell
    end tell
end goToDirectory

on setSavePanelFileName(appName, outputName)
    tell application "System Events"
        tell process appName
            tell window 1
                if exists splitter group 1 then
                    tell splitter group 1
                        if exists text field "Save As:" then
                            set value of text field "Save As:" to outputName
                            set focused of text field "Save As:" to true
                        else if exists text field "保存为：" then
                            set value of text field "保存为：" to outputName
                            set focused of text field "保存为：" to true
                        else if (count of text fields) >= 2 then
                            set value of text field 2 to outputName
                            set focused of text field 2 to true
                        else
                            set value of text field 1 to outputName
                            set focused of text field 1 to true
                        end if
                    end tell
                else if exists text field "Save As:" then
                    set value of text field "Save As:" to outputName
                    set focused of text field "Save As:" to true
                else if exists text field "保存为：" then
                    set value of text field "保存为：" to outputName
                    set focused of text field "保存为：" to true
                else if (count of text fields) >= 2 then
                    set value of text field 2 to outputName
                    set focused of text field 2 to true
                else
                    set value of text field 1 to outputName
                    set focused of text field 1 to true
                end if
            end tell
        end tell
    end tell
end setSavePanelFileName

on waitForFile(outputPath, timeoutSeconds)
    set startedAt to current date
    repeat
        try
            do shell script "test -f " & quoted form of outputPath
            return
        end try
        if ((current date) - startedAt) > timeoutSeconds then error "Timed out waiting for output file: " & outputPath
        delay 0.5
    end repeat
end waitForFile

on savePanelToPath(appName, outputPath, timeoutSeconds, shouldNavigate)
    set outputDirectory to do shell script "dirname " & quoted form of outputPath
    set outputName to do shell script "basename " & quoted form of outputPath

    my waitForSaveWindow(appName, timeoutSeconds)
    if shouldNavigate then
        my goToDirectory(appName, outputDirectory, timeoutSeconds)
        delay 0.4
    end if
    my setSavePanelFileName(appName, outputName)
    delay 0.2
    my clickFirstButtonByName(appName, {{"Save", "保存"}})
    delay 0.7
    my clickFirstButtonByName(appName, {{"Replace", "替换", "取代"}})
    delay 0.4
    my clickFirstButtonByName(appName, {{"Save", "保存"}})
    delay 0.4
    my clickButtonIfPresent(appName, "OK")
    my waitForFile(outputPath, timeoutSeconds)
end savePanelToPath

do shell script "open -a " & quoted form of appName & " " & quoted form of inputPath
my waitForProcess(appName, timeoutSeconds)
delay settleDelay
tell application appName to activate
delay 0.5
{save_block}{png_block}{quit_block}"""


def _build_save_block(request: ConversionRequest) -> str:
    if request.paths.gpx is None:
        return ""
    gpx_path = _as_string(str(request.paths.gpx))
    should_navigate = _as_boolean(request.paths.gpx.parent != request.paths.source.parent)
    menus = _as_applescript_menu_candidates(request.save_menu, DEFAULT_GPX_MENUS)
    return f"""
my clickFirstAvailableMenuPath({ _as_string(request.app_name) }, {menus}, timeoutSeconds)
delay 0.7
my savePanelToPath(appName, {gpx_path}, timeoutSeconds, {should_navigate})
delay settleDelay
"""


def _build_png_block(request: ConversionRequest) -> str:
    if request.paths.png is None:
        return ""
    png_path = _as_string(str(request.paths.png))
    should_navigate = _as_boolean(request.paths.png.parent != request.paths.source.parent)
    menus = _as_applescript_menu_candidates(request.png_menu, DEFAULT_PNG_MENUS)
    return f"""
my clickFirstAvailableMenuPath({ _as_string(request.app_name) }, {menus}, timeoutSeconds)
delay 0.7
my savePanelToPath(appName, {png_path}, timeoutSeconds, {should_navigate})
delay settleDelay
"""


def _as_applescript_list(values: tuple[str, ...]) -> str:
    return "{" + ", ".join(_as_string(value) for value in values) + "}"


def _as_applescript_menu_candidates(
    preferred: tuple[str, ...],
    defaults: tuple[tuple[str, ...], ...],
) -> str:
    ordered = (preferred, *tuple(candidate for candidate in defaults if candidate != preferred))
    return "{" + ", ".join(_as_applescript_list(candidate) for candidate in ordered) + "}"


def _as_boolean(value: bool) -> str:
    return "true" if value else "false"


def _as_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
