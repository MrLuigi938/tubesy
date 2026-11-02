# Benutzung

[← Zurück zur README](../../README.de.md) · [English](../en/usage.md)

- [Herunterladen](#herunterladen)
- [Playlists und Kanäle](#playlists-und-kanäle)
- [Presets](#presets)
- [Bibliothek](#bibliothek)
- [Ausgeblendete Videos](#ausgeblendete-videos)
- [Mehrere Videos auswählen](#mehrere-videos-auswählen)
- [Aufräumen](#aufräumen)
- [Abos](#abos)
- [Benachrichtigungen](#benachrichtigungen)
- [Teilen vom Smartphone](#teilen-vom-smartphone)
- [Benutzer, Einladungen und Kontingente](#benutzer-einladungen-und-kontingente)
- [Konto und Sitzungen](#konto-und-sitzungen)
- [API-Schlüssel und Dashboards](#api-schlüssel-und-dashboards)
- [Passwort vergessen?](#passwort-vergessen)

## Herunterladen

Unter **Downloads** einen Link einfügen und **Prüfen** klicken. Tubesy zeigt zuerst Titel, Kanal und Länge; dann ein Preset wählen und **Herunterladen**. Die Warteschlange zeigt Fortschritt, Geschwindigkeit und Restzeit live; Downloads lassen sich abbrechen und fehlgeschlagene wiederholen.

YouTube, YouTube Music und über 1000 weitere Seiten funktionieren – **Welche Seiten werden unterstützt?** unter dem Eingabefeld listet alle auf. Direkte Links auf Video- oder Audiodateien gehen immer.

**Trotzdem herunterladen:** Schlägt die Prüfung fehl (z. B. *Unsupported URL* oder Zeitüberschreitung), bietet die Fehlermeldung an, den Link trotzdem einzureihen. Tubesy geht dann Schritt für Schritt vor:

1. **yt-dlp** noch einmal, die Seite wird dabei wie von einem Browser abgerufen.
2. **Ein echter Browser:** Tubesy öffnet die Seite in einem Chromium im Hintergrund, startet den Player (stumm) und schaut mit, welche Streams (`.m3u8`, `.mpd`) oder Videodateien er lädt – auch in eingebetteten Playern. Der beste Fund wird mit den Cookies des Browsers und der Seite als Referer geladen. So werden auch Videos gefunden, die erst JavaScript zusammensetzt.
3. **Der Seitenquelltext:** `<video>`-Tags, `og:video`-Angaben sowie Stream- und Dateiadressen in der Seite und ihren Skripten – der Rückfall, wenn kein Browser vorhanden ist.

Vor dem Download **misst Tubesy jedes gefundene Video** und nimmt das längste – Werbeclips vor dem Film und Lockvideos im Seitenquelltext gehen leer aus.

Die Datei wird nach der Seite benannt. Die Warteschlange zeigt jeden Schritt; wird nichts gefunden, steht das dort. **DRM-geschützte Streams** (Netflix, Disney+, Prime Video …) sind verschlüsselt und lassen sich nicht herunterladen. Manche Hoster sperren außerdem jeden Download aus, der nicht aus dem Browser eines echten Menschen kommt (Bot-Schutz); das umgeht Tubesy nicht.

## Playlists und Kanäle

Ein Playlist- oder Kanal-Link listet alle Videos auf (bis zum Limit unter *Verwaltung → Einstellungen*). Einzelne Videos oder alle auswählen; mit **Eigener Ordner** landen sie in einem Ordner mit dem Namen der Playlist, durchnummeriert (`001 - …`). Ein Kanal-Link ohne Reiter lädt die Videos des Kanals.

## Presets

Presets bestimmen Qualität und Format: maximale Auflösung, Container (MP4 läuft überall, MKV, WebM), nur Audio (MP3, M4A, Opus, FLAC, WAV), Untertitel, eingebettetes Vorschaubild, Metadaten und Kapitel, SponsorBlock (Sponsor-Abschnitte, Intros … herausschneiden) und die Dateinamen-Vorlage.

Globale Presets legen Administratoren an, sie sind für alle sichtbar; jeder Benutzer kann eigene anlegen und mit **Als Standard** einen Standard wählen. Rohe yt-dlp-Argumente sind bewusst nicht möglich, weil Optionen wie `--exec` Befehle auf dem Server ausführen könnten.

## Bibliothek

Alle fertigen Downloads – suchen, im Browser abspielen, aufs eigene Gerät herunterladen oder löschen (wahlweise mit Datei). Unter **Playlists** ist jede Playlist eine Sammlung, die sich auf einmal als ZIP herunterladen lässt.

Nicht jeder Browser spielt jedes Format ab (z. B. MKV in Safari); herunterladen geht immer.

## Ausgeblendete Videos

Ein Privatsphäre-Modus für 18+-Inhalte oder alles, was privat bleiben soll.

- **Ausblenden** mit dem Auge-Symbol – in der Warteschlange, in der Bibliothek oder für eine ganze Playlist (Playlist-Seite → Auge) – oder vor dem Herunterladen **Ausblenden** ankreuzen.
- **Automatisch bei 18+:** Liefert eine Seite eine Altersfreigabe ab 18 (z. B. YouTube), wird das Video beim Herunterladen ausgeblendet. Abschalten unter **Konto → Privatsphäre**.
- Ausgeblendete Videos sind überall **verdeckt**: kein Vorschaubild, *Ausgeblendetes Video* statt Titel, Kanal und Dateiname. **Antippen zum Anzeigen** deckt eines für die aktuelle Ansicht auf; beim Verlassen der Seite ist es wieder verdeckt. Der Server schickt die Angaben erst beim Aufdecken.
- Sie stehen **nicht zwischen den anderen Videos**: der Reiter **Ausgeblendet** in der Bibliothek listet alle (auch aus Playlists).
- **Dashboards und die API sehen sie nie:** In der Warteschlange von [Heimdeck](https://github.com/MrLuigi938/heimdeck) erscheint ein ausgeblendeter Download als *Ausgeblendetes Video* ohne Bild, und in Suchen taucht er gar nicht auf. Mit dem Auge-Symbol wieder einblenden.

## Mehrere Videos auswählen

**Auswählen** in der Bibliothek (Videos, Playlists und Ausgeblendet) blendet Kästchen ein. Videos einzeln oder mit **Alle auswählen** markieren, dann:

- **Als ZIP** – lädt die fertigen Dateien in einem Archiv (Playlists als Ordner)
- **Ausblenden** / **Einblenden**
- **Löschen** – mit oder ohne Dateien; laufende Downloads werden übersprungen

Auf dem Smartphone bleiben die Aktionen unten am Bildschirmrand.

## Aufräumen

**Bibliothek → Aufräumen…** löscht auf einmal alle deine einzelnen Videos, alle Playlists oder alles:

1. Auswählen, was gelöscht wird und ob die Dateien mitgehen.
2. Tubesy zeigt, was das bedeutet – *Wirklich 42 Videos und 3 Playlists (61 GB) löschen?* – und erst dann löscht der rote Button.

Laufende und wartende Downloads bleiben. Ausgeblendete Videos sind eingeschlossen, Downloads anderer Benutzer nie.

**Automatisch:** Unter **Konto → Automatisch aufräumen** lassen sich deine fertigen Downloads nach einer Anzahl Tage löschen (mit Dateien, einmal pro Stunde geprüft). Administratoren können unter *Verwaltung → Einstellungen* zusätzlich *Aufräumen, wenn weniger frei ist als* setzen: Tubesy löscht dann die ältesten fertigen Downloads aller Benutzer, bis wieder genug Platz ist.

## Abos

**Abos** lädt die neuen Videos von Kanälen und Playlists von selbst herunter.

1. Einen Kanal- oder Playlist-Link einfügen (oder nach dem Prüfen einer Playlist auf der Download-Seite **Abonnieren** klicken).
2. Preset wählen, wie oft Tubesy nach neuen Videos sieht (stündlich bis wöchentlich) und ob die neuesten 3–25 Videos gleich mitkommen sollen – sonst nur Videos, die ab jetzt erscheinen.
3. Mit **Eigener Ordner** landen die Videos in einem Ordner mit dem Namen des Kanals und erscheinen in der Bibliothek als Playlist; **Ausblenden** blendet jedes neue Video aus.

Tubesy merkt sich jedes Video, das ein Abo schon kennt – gelöschte Downloads werden nie noch einmal geladen. Abos lassen sich sofort prüfen, pausieren, bearbeiten und beenden; geladene Videos bleiben.

## Benachrichtigungen

**Konto → Benachrichtigungen** schickt eine Nachricht, wenn ein Download fertig oder fehlgeschlagen ist – bei Playlists und Abos eine für alle Videos zusammen. Ausgeblendete Videos werden nie genannt.

- **Im Browser:** solange Tubesy im Hintergrund geöffnet ist (der Browser fragt einmal nach der Erlaubnis).
- **ntfy:** die Adresse des Themas, z. B. `https://ntfy.sh/mein-geheimes-thema` oder dein eigener ntfy-Server, wahlweise mit Zugangs-Token.
- **Telegram:** das Token deines Bots (von @BotFather) und deine Chat-ID.

**Test senden** prüft die Einstellungen sofort.

## Teilen vom Smartphone

Tubesy lässt sich als App installieren (Browsermenü → *App installieren* / *Zum Startbildschirm* oder **Konto → App**). Browser installieren Web-Apps nur über **HTTPS** – rufe Tubesy über deinen [Reverse Proxy](reverse-proxy.md) mit `https://` auf; über `http://<ip>:8080` im Heimnetz bieten sie höchstens eine Verknüpfung an. Unter Android erscheint es dann im Teilen-Menü: ein Video aus der YouTube-App an **Tubesy** teilen, und die Prüfung startet sofort.

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
