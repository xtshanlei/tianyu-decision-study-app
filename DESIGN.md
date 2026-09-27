# Study chat design

## 1. Atmosphere

A calm, professional research conversation. The existing warm paper canvas and dark green action color remain. The conversation is the main object on the page; no decorative imagery is needed. The interface must give Option A and Option B equal visual weight and never reveal the experimental condition.

The supplied Word document defines the content and sequence. The existing interface and its minimalist editorial direction are the visual reference for this update.

## 2. Colors

| Token | Value | Use |
| --- | --- | --- |
| Canvas | `#FAF9F7` | Page background |
| Surface | `#FFFFFF` | Assistant messages and forms |
| Participant | `#EAF0ED` | Participant messages |
| Text | `#242320` | Primary copy |
| Muted | `#62605C` | Labels and progress |
| Border | `#E7E4DF` | Surface boundaries |
| Action | `#2E4A46` | Primary button |
| Action hover | `#233B37` | Button hover |

## 3. Typography

Use Georgia for the page title at 32 px. Keep Streamlit's readable system sans serif for all study content and controls. Body copy uses a relaxed 1.55 line height; metadata is 13 px.

CSS tokens: `--title-font`, `--title-size`, `--title-leading`, `--title-tracking`, `--body-leading`, and `--metadata-size`.

## 4. Spacing and layout

Center content in a 760 px column, with 52 px top and 64 px bottom padding on desktop. Use a 4 px spacing unit. Below 600 px, use 16 px side padding. Conversation messages stack in chronological order, indented by 48 px on desktop and 18 px on mobile, while remaining inside the column. The fixed-question action spans the available width.

CSS tokens: `--content-width`, `--page-top`, `--page-bottom`, `--mobile-page-top`, `--mobile-page-side`, `--mobile-page-bottom`, `--chat-indent`, `--mobile-chat-indent`, and `--chat-gap`.

## 5. Components and states

- **Study header:** compact research label, title, and one instruction sentence.
- **Assistant message:** case introduction and each generated answer in the same chat thread; white surface.
- **Participant message:** initial Option A/B choice and free sentence, then each fixed question; soft green surface.
- **Role avatars:** use Streamlit's accessible role icons in dark green for the assistant and white on dark green for the participant.
- **Initial position composer:** Option A/B radio, one-sentence text field, and a primary Continue button. Invalid input shows an inline error and remains editable.
- **Fixed question composer:** one primary button containing the next fixed question. On click, show the submitted question and an assistant loading state until the answer arrives. On failure, show an error and keep the question available for retry.
- **Progress and completion:** a small round label and progress indicator; completion is a short status after the final answer.

The transcript is reconstructed from persisted participant and turn records on every load, including after a refresh.

## 6. Motion

Use Streamlit's native spinner only while waiting for the model. Do not add decorative motion. Honor the browser's reduced-motion preference through the framework defaults.

## 7. Depth and surfaces

Chat bubbles use a subtle border and 8 px corners. Keep shadows absent to preserve the research tone. The page canvas remains warm and the message backgrounds provide the contrast.

## 8. Accessibility and accepted debt

Keep semantic Streamlit chat roles (`user`, `assistant`), visible text labels, keyboard-operable radio/text/button controls, readable contrast, and responsive wrapping. Streamlit owns message focus and screen-reader behavior. The fixed question is a button so participants cannot add unscripted messages after the initial view.
