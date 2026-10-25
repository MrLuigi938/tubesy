# Benutzung

[← Zurück zur README](../../README.de.md) · [English](../en/usage.md)

- [Herunterladen](#herunterladen)
- [Playlists und Kanäle](#playlists-und-kanäle)
- [Presets](#presets)
- [Bibliothek](#bibliothek)
- [Teilen vom Smartphone](#teilen-vom-smartphone)
- [Benutzer, Einladungen und Kontingente](#benutzer-einladungen-und-kontingente)
- [Konto und Sitzungen](#konto-und-sitzungen)
- [API-Schlüssel und Dashboards](#api-schlüssel-und-dashboards)
- [Passwort vergessen?](#passwort-vergessen)

## Herunterladen

Unter **Downloads** einen Link einfügen und **Prüfen** klicken. Tubesy zeigt zuerst Titel, Kanal und Länge; dann ein Preset wählen und **Herunterladen**. Die Warteschlange zeigt Fortschritt, Geschwindigkeit und Restzeit live; Downloads lassen sich abbrechen und fehlgeschlagene wiederholen.

YouTube, YouTube Music und über 1000 weitere Seiten funktionieren – **Welche Seiten werden unterstützt?** unter dem Eingabefeld listet alle auf. Direkte Links auf Video- oder Audiodateien gehen immer.

## Playlists und Kanäle

Ein Playlist- oder Kanal-Link listet alle Videos auf (bis zum Limit unter *Verwaltung → Einstellungen*). Einzelne Videos oder alle auswählen; mit **Eigener Ordner** landen sie in einem Ordner mit dem Namen der Playlist, durchnummeriert (`001 - …`). Ein Kanal-Link ohne Reiter lädt die Videos des Kanals.

## Presets

Presets bestimmen Qualität und Format: maximale Auflösung, Container (MP4 läuft überall, MKV, WebM), nur Audio (MP3, M4A, Opus, FLAC, WAV), Untertitel, eingebettetes Vorschaubild, Metadaten und Kapitel, SponsorBlock (Sponsor-Abschnitte, Intros … herausschneiden) und die Dateinamen-Vorlage.

Globale Presets legen Administratoren an, sie sind für alle sichtbar; jeder Benutzer kann eigene anlegen und mit **Als Standard** einen Standard wählen. Rohe yt-dlp-Argumente sind bewusst nicht möglich, weil Optionen wie `--exec` Befehle auf dem Server ausführen könnten.

## Bibliothek

Alle fertigen Downloads – suchen, im Browser abspielen, aufs eigene Gerät herunterladen oder löschen (wahlweise mit Datei). Unter **Playlists** ist jede Playlist eine Sammlung, die sich auf einmal als ZIP herunterladen lässt.

Nicht jeder Browser spielt jedes Format ab (z. B. MKV in Safari); herunterladen geht immer.

## Teilen vom Smartphone

Tubesy lässt sich als App installieren (Browsermenü → *App installieren* / *Zum Startbildschirm*). Unter Android erscheint es dann im Teilen-Menü: ein Video aus der YouTube-App an **Tubesy** teilen, und die Prüfung startet sofort.

Am Computer geht auch ein Lesezeichen: `https://<dein-tubesy>/?url=` gefolgt vom Link öffnet Tubesy damit.

## Benutzer, Einladungen und Kontingente

**Verwaltung → Benutzer:** Benutzer anlegen, zu Administratoren machen, Passwort setzen, sperren oder ein Speicherkontingent festlegen. Jeder Benutzer hat seinen eigenen Ordner und sieht nur seine Downloads; Administratoren sehen alles unter **Verwaltung → Alle Downloads**.

**Verwaltung → Einladungen:** Einladungslinks erzeugen (für eine oder mehrere Personen, gültig 1/7/30 Tage oder unbegrenzt, wahlweise als Administrator). Der Link wird nur einmal angezeigt. Die Registrierung kann auch *offen* oder *geschlossen* sein.

## Konto und Sitzungen

Unter **Konto** sieht jeder seinen Speicherverbrauch, ändert Passwort und Sprache und sieht alle Geräte, auf denen er angemeldet ist – unbekannte Sitzungen lassen sich dort beenden.

## API-Schlüssel und Dashboards

**Konto → API-Schlüssel** erzeugt einen Schlüssel für Dashboards (z. B. [Heimdeck](https://github.com/MrLuigi938/heimdeck)), Skripte oder Kurzbefehle – *nur lesen* oder *lesen & Downloads*. Details: [API](api.md).

## Passwort vergessen?

Ein Administrator kann unter **Verwaltung → Benutzer** ein neues Passwort setzen. Kann sich kein Administrator mehr anmelden, auf dem Server zurücksetzen:

```sh
# Docker
docker exec -it tubesy python -m app.cli reset-password <benutzer> <neues-passwort>
# ohne Docker
sudo -u tubesy sh -c 'set -a; . /etc/default/tubesy; cd /opt/tubesy && venv/bin/python -m app.cli reset-password <benutzer> <neues-passwort>'
```

Das entsperrt außerdem das Konto und meldet alle seine Sitzungen ab.
