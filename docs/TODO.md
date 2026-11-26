# MySpott: To Do

- [x] Phase 0: SRS review and plan
- [x] Phase 1: Foundation
- [x] Phase 2: Database foundation
- [x] Phase 3: Authentication
- [x] Phase 4: Web UI foundation (design system, page frame, account pages, component kit)
- [ ] Phase 5: Property core (models, create/edit/pause/publish, owner dashboard)
- [ ] Phase 6: Images (upload, validation, compression, thumbnails, cloud storage)
- [ ] Phase 7: Facilities and house rules
- [ ] Phase 8: Discovery (list, filters, sorting, pagination, detail page)
- [ ] Phase 9: Maps and location (pin picker, map view, "distance to a place you choose", nearby places)
- [ ] Phase 10: Contact reveal (protected WhatsApp endpoint, rate limiting)
- [ ] Phase 11: AI checks and moderation (quality, duplicates, risk flags, reports, admin)
- [ ] Phase 12: Hardening and web release (see list below)
- [ ] Phase 13: Android app (Expo)
- [ ] Phase 14: iOS app
- [ ] Phase 15: End-to-end testing and release

## Carried over to Phase 12 (hardening and deployment)
- Configure the hosting proxy so visitor addresses are read correctly (otherwise rate limits see one address)
- Move rate-limit counters to a shared store (Redis)
- Send emails in the background so the reset form answers equally fast for every address
- Choose and test a real email service over SMTP
- Pin exact versions of every package in requirements.txt
- Self-host the Inter font and add a content security policy (possible now: no inline scripts or styles)
- Cache-busting for the stylesheet and script, security headers, backups, monitoring

## Open decisions
- Which details an owner must enter for a listing (decided at the start of Phase 5)
- Image storage provider, hosting provider
- Default map area for first-time visitors (Phase 9)