# Analytics service intentionally retired

The original Quiet.md source repository contained an optional Cloudflare
Workers/D1 analytics service. It queried **Quiet.md's** Cloudflare zone,
download domain, and GitHub repository. Those endpoints and account settings
do not belong to GoreeCloud, and deploying that service would not be an
appropriate part of this independent rebrand.

The executable worker, scheduled backfill, D1 migration, and deployment
configuration were intentionally removed from the GoreeCloud import.
**No stats worker is provisioned, scheduled, or needed to run the desktop app.**

For historical source and attribution, see [UPSTREAM.md](../../UPSTREAM.md).
If GoreeCloud ever opts into independent, privacy-respecting aggregate
analytics, that should be a separately reviewed project with explicitly
GoreeCloud-owned infrastructure and credentials; do not reuse upstream IDs.
