package main

import (
	"archive/zip"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// ── Config ──────────────────────────────────────────────

const (
	r2URL            = "https://update.onelaunch.pp.ua"
	versionURL       = r2URL + "/version.json"
	localVersionFile = "version.txt"
	appDir           = "_app"
	appExe           = "OneLaunch_App.exe"
	updateZipName    = "update_temp.zip"
)

type VersionInfo struct {
	Version string `json:"version"`
	URL     string `json:"url"`
}

// ── Main ────────────────────────────────────────────────

func main() {
	localVer := getLocalVersion()
	logMsg(fmt.Sprintf("Local version: %s", localVer))

	// 1. Check version on Cloudflare R2
	remote, err := fetchVersion()
	if err != nil {
		logMsg(fmt.Sprintf("Version check failed: %v", err))
		startMainApp()
		return
	}
	logMsg(fmt.Sprintf("Remote version: %s", remote.Version))

	// 2. If versions differ — download and extract
	if compareVersions(remote.Version, localVer) > 0 {
		logMsg(fmt.Sprintf("Update available: %s -> %s", localVer, remote.Version))
		if err := downloadAndExtract(remote.URL); err != nil {
			logMsg(fmt.Sprintf("Update failed: %v", err))
			startMainApp()
			return
		}
		// Write new version AFTER successful extraction
		_ = os.WriteFile(localVersionFile, []byte(remote.Version), 0644)
		logMsg(fmt.Sprintf("Updated to %s", remote.Version))
	} else {
		logMsg("Already up to date")
	}

	// 3. Start main app
	startMainApp()
}

// ── Helpers ─────────────────────────────────────────────

func logMsg(msg string) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	fmt.Printf("[%s] %s\n", timestamp, msg)
}

func getLocalVersion() string {
	data, err := os.ReadFile(localVersionFile)
	if err != nil {
		return "0.0.0"
	}
	return strings.TrimSpace(string(data))
}

func fetchVersion() (*VersionInfo, error) {
	client := http.Client{Timeout: 15 * time.Second}
	resp, err := client.Get(versionURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	var info VersionInfo
	if err := json.NewDecoder(resp.Body).Decode(&info); err != nil {
		return nil, err
	}
	return &info, nil
}

// compareVersions returns 1 if a > b, -1 if a < b, 0 if equal.
func compareVersions(a, b string) int {
	partsA := parseVersion(a)
	partsB := parseVersion(b)
	for i := 0; i < 3; i++ {
		if partsA[i] > partsB[i] {
			return 1
		}
		if partsA[i] < partsB[i] {
			return -1
		}
	}
	return 0
}

func parseVersion(v string) [3]int {
	var parts [3]int
	fmt.Sscanf(v, "%d.%d.%d", &parts[0], &parts[1], &parts[2])
	return parts
}

func startMainApp() {
	exePath := filepath.Join(appDir, appExe)
	if _, err := os.Stat(exePath); os.IsNotExist(err) {
		logMsg(fmt.Sprintf("Main app not found: %s", exePath))
		return
	}

	cmd := exec.Command(exePath)
	cmd.Stdout = nil
	cmd.Stderr = nil
	_ = cmd.Start()
	logMsg(fmt.Sprintf("Started: %s", exePath))
	os.Exit(0)
}

// ── Download & Extract ─────────────────────────────────

func downloadAndExtract(url string) error {
	// 1. Download archive
	logMsg("Downloading update...")
	resp, err := http.Get(url)
	if err != nil {
		return fmt.Errorf("download: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("download HTTP %d", resp.StatusCode)
	}

	out, err := os.Create(updateZipName)
	if err != nil {
		return fmt.Errorf("create temp file: %w", err)
	}

	written, err := io.Copy(out, resp.Body)
	out.Close()
	if err != nil {
		os.Remove(updateZipName)
		return fmt.Errorf("write temp file: %w", err)
	}
	logMsg(fmt.Sprintf("Downloaded %.1f MB", float64(written)/(1024*1024)))
	defer os.Remove(updateZipName)

	// 2. Extract to _app_new/ (avoid locking running _app/)
	newAppDir := "_app_new"
	_ = os.RemoveAll(newAppDir) // clean previous failed attempt

	if err := extractZip(updateZipName, newAppDir); err != nil {
		os.RemoveAll(newAppDir)
		return fmt.Errorf("extract: %w", err)
	}

	// 3. Swap: _app -> _app_old, _app_new -> _app
	oldAppDir := "_app_old"
	_ = os.RemoveAll(oldAppDir)

	// Try rename with retry (file locks may linger)
	if err := retryRename(appDir, oldAppDir, 5); err != nil {
		os.RemoveAll(newAppDir)
		return fmt.Errorf("swap (remove old): %w", err)
	}
	if err := retryRename(newAppDir, appDir, 5); err != nil {
		// Try to restore old app
		os.Rename(oldAppDir, appDir)
		return fmt.Errorf("swap (move new): %w", err)
	}

	// Clean up old version
	os.RemoveAll(oldAppDir)
	logMsg("Update installed successfully")
	return nil
}

func extractZip(zipPath, destDir string) error {
	r, err := zip.OpenReader(zipPath)
	if err != nil {
		return err
	}
	defer r.Close()

	for _, f := range r.File {
		// Clean path to prevent zip-slip
		fpath := filepath.Join(destDir, filepath.Clean(f.Name))
		if !strings.HasPrefix(fpath, filepath.Clean(destDir)+string(os.PathSeparator)) {
			return fmt.Errorf("illegal path: %s", f.Name)
		}

		if f.FileInfo().IsDir() {
			os.MkdirAll(fpath, os.ModePerm)
			continue
		}

		if err := os.MkdirAll(filepath.Dir(fpath), os.ModePerm); err != nil {
			return err
		}

		outFile, err := os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			return err
		}

		rc, err := f.Open()
		if err != nil {
			outFile.Close()
			return err
		}

		_, err = io.Copy(outFile, rc)
		outFile.Close()
		rc.Close()
		if err != nil {
			return err
		}
	}
	return nil
}

func retryRename(oldPath, newPath string, maxRetries int) error {
	var lastErr error
	for i := 0; i < maxRetries; i++ {
		if i > 0 {
			time.Sleep(time.Duration(i) * 500 * time.Millisecond)
		}
		if err := os.Rename(oldPath, newPath); err == nil {
			return nil
		} else {
			lastErr = err
		}
	}
	return fmt.Errorf("rename after %d retries: %w", maxRetries, lastErr)
}
