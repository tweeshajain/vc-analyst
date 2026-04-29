"""Mock Product Hunt posts when the API is unavailable (no token or network error)."""

from modules.radar.types import TrendingStartup

MOCK_PRODUCT_HUNT_POSTS: tuple[TrendingStartup, ...] = (
    TrendingStartup(
        name="Nimbus Docs",
        description="AI-native collaborative docs with live research citations.",
        url="https://www.producthunt.com/posts/nimbus-docs-mock",
        upvotes=842,
        comments_count=56,
        source="product_hunt",
        external_id="mock_ph_nimbus",
        sector="Productivity",
        stage="",
    ),
    TrendingStartup(
        name="LedgerKit",
        description="Startup finance cockpit: runway, burn, and cohort revenue.",
        url="https://www.producthunt.com/posts/ledgerkit-mock",
        upvotes=610,
        comments_count=41,
        source="product_hunt",
        external_id="mock_ph_ledgerkit",
        sector="Fintech",
        stage="",
    ),
    TrendingStartup(
        name="VoiceWeave",
        description="Real-time voice translation for global sales calls.",
        url="https://www.producthunt.com/posts/voiceweave-mock",
        upvotes=523,
        comments_count=38,
        source="product_hunt",
        external_id="mock_ph_voiceweave",
        sector="AI",
        stage="",
    ),
)
