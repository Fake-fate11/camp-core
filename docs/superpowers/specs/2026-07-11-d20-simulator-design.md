# D20 Simulator Design

## Goal

Provide a small d20 simulator that runs offline by double-clicking a single HTML file.

## User Experience

- Show one centered, dark tabletop-style card.
- Display a prominent d20 shape with the current result.
- Roll once when the user clicks the primary button or presses the Space key.
- Play a short number-changing animation before settling on the final result.
- Keep the eight most recent results visible for the current page session.
- Keep the layout usable on desktop and mobile-sized windows.

## Implementation

Create one standalone HTML file with inline CSS and JavaScript. Use no external assets, libraries, network requests, build tools, or storage.

Generate each final result with `crypto.getRandomValues()` and rejection sampling so every integer from 1 through 20 has equal probability. The animation may show temporary visual-only values; only the final result is added to history.

Use semantic HTML, a real button, a visible keyboard focus state, and reduced-motion handling. Ignore Space-key rolls while focus is in another interactive control, and prevent overlapping rolls while the animation is active.

## Verification

- Open the file directly from disk in a modern browser.
- Confirm button clicks and Space-key presses each produce a result from 1 through 20.
- Confirm rapid repeated input does not create overlapping rolls.
- Confirm history keeps only the latest eight final results.
- Confirm reduced-motion mode skips the rolling animation while still producing a result.

## Out of Scope

Multiple dice, modifiers, saved history, sound, themes, 3D physics, and online deployment are not included.
