# MySpott: Design Guide

The rules behind the look and feel of MySpott. The single source of truth for colours, sizes and
spacing is the `:root` block at the top of `app/static/css/app.css`. To see every component at once,
run the site and open `/dev/style-guide` (development only).

## Brand
- Name: MySpott ("My" in a light weight, "Spott" in bold teal). Logo: a map pin in a rounded teal square.
- Voice: friendly, plain and honest. Short sentences, no jargon. Say what happened and what to do next.
- Typeface: Inter (weights 400, 500, 600, 700), then the system font as a fallback.
- Audience: anyone looking to rent a home, not only students.

## Colours
| Token | Value | Use |
|-------|-------|-----|
| color-primary | #0E7C86 | Main buttons, links, the logo |
| color-primary-hover | #0B656D | Hover state, text on tinted backgrounds |
| color-primary-tint | #E6F4F5 | Soft backgrounds (hero, tags, selected cards) |
| color-highlight | #F5B83D | Small highlights such as the "New" badge (dark text on it) |
| color-ink | #1F2937 | Main text |
| color-muted | #566070 | Hints and secondary text |
| color-page | #F7F8FA | Page background |
| color-surface | #FFFFFF | Cards, header, fields |
| color-border / border-strong | #E3E7EC / #CBD2D9 | Lines and field borders |
| success / warning / danger | #16794A / #8A5300 / #B3261E | Status text, each with a soft tint background |

Never write a colour value outside the `:root` block. Use the variable.
Contrast of every text and background pair is tested (at least 4.5 to 1).

## Type, space and shape
- Headings: h1 1.75 to 2.5rem bold (scales with the screen), h2 1.5rem semibold, h3 1.125rem semibold.
- Body 1rem with 1.6 line height. Small text 0.875rem.
- Spacing scale (variables `--space-1` to `--space-7`): 4, 8, 12, 16, 24, 32 and 48 px.
- Corners: cards 12px, buttons and fields 10px, pills fully round. Shadows are subtle.

## Layout
- Mobile first. Page width is capped at 72rem. Breakpoints: 40rem (small tablets) and 48rem (desktop menu).
- Nothing may scroll sideways. Fields and normal buttons are at least 44px tall (touch friendly).
- Every page has: skip link, header with menu, messages area, main content, footer.

## Components
| Need | Use | Notes |
|------|-----|-------|
| Main action | `btn btn-primary` | One per view |
| Other actions | `btn btn-secondary`, `btn-ghost`, `btn-danger`, size `btn-sm`, full width `btn-block` | |
| Form field | `div.field` with label, input, `field__hint`, `field__error` | See account pages |
| Password | `password-field` with a `data-password-toggle` button | |
| Choice cards | `fieldset.option-cards` with `option-card` labels | |
| Messages | flashed messages (`success`, `info`, `warning`, `error`) | Built in `base.html` |
| Form error summary | `form-alert` with `role="alert"` | Plus the message under each field |
| Cards | `card` | |
| Listing card | macro `property_card(...)` | In `templates/components/ui.html` |
| Empty list | macro `empty_state(...)` | Explain the area and offer the next action |
| Loading | macro `skeleton_card()` | And "please wait" on submit buttons |
| Ask before deleting | macro `confirm_form(...)` | Always ALSO check permissions on the server |
| Tags and badges | `tag-list` / `tag`, `badge`, `badge-highlight` | |

## Rules
1. One primary button per view.
2. Every field has a visible label. Errors appear under the field, linked with `aria-describedby`,
   and the field gets `aria-invalid="true"`.
3. Destructive actions ask first (`confirm_form`), and the server never relies on that question.
4. Messages are short and kind. One message per event.
5. No inline styles or scripts, and no new colours outside the variables (tested for templates).
6. Every form that posts data has a security token and every button has a type (tested).
7. Anything new that is reusable goes into `components/ui.html` and the style guide page.
8. Accessibility: contrast of at least 4.5 to 1, visible keyboard focus, headings in order,
   reduced motion respected, the site works without JavaScript (the confirmation dialog is the one
   exception: without JavaScript the form is sent without asking).
9. Money is shown with the rupee sign and Indian digit grouping (a template filter comes in Phase 5).

## JavaScript hooks (`app/static/js/app.js`)
| Attribute | Effect |
|-----------|--------|
| `data-nav-toggle`, `data-nav-menu` | Phone menu button and the menu it opens |
| `data-password-toggle` (+ `aria-controls`) | Show or hide a password |
| `data-submit-once`, `data-loading-text` | Button shows "please wait" and a double click is ignored |
| `data-dismissible`, `data-dismiss` | A message box with a close button |
| `data-confirm`, `-title`, `-label`, `-tone` | Ask "are you sure?" before the form is sent |

## Files
- `app/static/css/app.css`: the stylesheet (tokens, base, layout, header, buttons, forms, messages, components, account pages, component kit, style guide)
- `app/static/js/app.js`: the only script
- `app/static/img/favicon.svg`: the tab icon
- `app/templates/base.html`: the page frame; `components/ui.html`: reusable macros; `dev/style_guide.html`: the style guide