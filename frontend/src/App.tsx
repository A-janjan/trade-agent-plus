import { Link } from "react-router-dom";
import RecentRuns from "./components/RecentRuns";
import RunForm from "./components/RunForm";
import Icon from "./components/Icon";

const WORKFLOW = [
    { number: "01", title: "Investigate", text: "Independent lenses gather market, social, news, and fundamental evidence.", icon: "search" as const },
    { number: "02", title: "Challenge", text: "Research and risk debates pressure-test the story from opposing angles.", icon: "shield" as const },
    { number: "03", title: "Decide", text: "A portfolio manager turns the transcript into a clear, auditable stance.", icon: "sparkles" as const },
];

export default function App() {
    return (
        <div className="app-page home-page">
            <header className="topbar shell">
                <Link className="brand" to="/" aria-label="tradeagents home">
                    <span className="brand-mark"><Icon name="spark" size={17} /></span>
                    <span>trade<span>agents</span></span>
                </Link>
                <nav className="topnav" aria-label="Primary navigation">
                    <a href="#new-run">New run</a>
                    <a href="#method">Method</a>
                    <a href="#history">History</a>
                </nav>
                <div className="topbar-status"><span /> Research workspace</div>
            </header>

            <main className="shell home-main">
                <section className="home-hero">
                    <div className="hero-copy">
                        <div className="eyebrow"><span className="eyebrow-dot" /> Multi-agent market intelligence <span className="eyebrow-tag">v0.1</span></div>
                        <h1>Make the next decision feel <em>less like a guess.</em></h1>
                        <p className="hero-lede">A research room of independent analysts, adversarial debates, and one accountable final call — streamed live as the evidence comes together.</p>
                        <div className="hero-stats">
                            <div><strong>4</strong><span>research lenses</span></div>
                            <div><strong>2</strong><span>adversarial debates</span></div>
                            <div><strong>1</strong><span>auditable decision</span></div>
                        </div>
                    </div>
                    <div className="hero-visual" aria-hidden="true">
                        <div className="visual-glow" />
                        <div className="visual-label visual-label-top"><span className="mini-dot green" /> evidence graph</div>
                        <svg className="hero-chart" viewBox="0 0 520 330" role="presentation">
                            <defs>
                                <linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1">
                                    <stop offset="0" stopColor="#b9f86b" stopOpacity=".25" />
                                    <stop offset="1" stopColor="#b9f86b" stopOpacity="0" />
                                </linearGradient>
                                <linearGradient id="chartLine" x1="0" x2="1" y1="1" y2="0">
                                    <stop offset="0" stopColor="#63d8c2" />
                                    <stop offset="1" stopColor="#d5ff7d" />
                                </linearGradient>
                            </defs>
                            <g className="chart-grid">
                                <path d="M48 42H485M48 100H485M48 158H485M48 216H485M48 274H485" />
                                <path d="M48 42V274M157 42V274M266 42V274M375 42V274M485 42V274" />
                            </g>
                            <path className="chart-area" d="M48 235 92 214 125 226 166 167 198 183 235 146 277 161 319 106 353 128 395 84 432 103 485 48V274H48Z" />
                            <path className="chart-path" d="M48 235 92 214 125 226 166 167 198 183 235 146 277 161 319 106 353 128 395 84 432 103 485 48" />
                            <circle className="chart-point" cx="395" cy="84" r="6" />
                            <circle className="chart-point-ring" cx="395" cy="84" r="13" />
                            <g className="chart-axis"><text x="48" y="300">evidence in</text><text x="432" y="300">decision</text></g>
                        </svg>
                        <div className="visual-node node-one"><Icon name="trend" size={15} /><span>market</span></div>
                        <div className="visual-node node-two"><Icon name="globe" size={15} /><span>news</span></div>
                        <div className="visual-node node-three"><Icon name="shield" size={15} /><span>risk</span></div>
                        <div className="visual-center"><Icon name="sparkles" size={21} /><span>PM</span></div>
                        <div className="visual-label visual-label-bottom">signal / thesis / risk</div>
                    </div>
                </section>

                <section className="workspace-section" id="new-run">
                    <RunForm />
                    <aside className="workspace-aside">
                        <div className="aside-card panel">
                            <div className="aside-icon"><Icon name="eye" size={18} /></div>
                            <div>
                                <span className="eyebrow">What you get</span>
                                <h3>See the reasoning, not just the rating.</h3>
                                <p>Every report, debate turn, tool call, and final stance is kept in one live transcript.</p>
                            </div>
                        </div>
                        <div className="signal-card panel">
                            <div className="signal-header"><span>Decision quality loop</span><span className="signal-live"><span /> online</span></div>
                            <div className="signal-line"><span className="signal-line-progress" /></div>
                            <div className="signal-foot"><span>log</span><Icon name="arrowRight" size={13} /><span>settle</span><Icon name="arrowRight" size={13} /><span>reflect</span><Icon name="arrowRight" size={13} /><span>inject</span></div>
                        </div>
                        <div className="disclaimer-card"><Icon name="shield" size={15} /><span>Built for research and evaluation — not order execution.</span></div>
                    </aside>
                </section>

                <section className="method-section" id="method" aria-labelledby="method-title">
                    <div className="section-heading method-heading">
                        <div>
                            <div className="eyebrow"><Icon name="zap" size={14} /> The research loop</div>
                            <h2 id="method-title">From raw signal to considered stance.</h2>
                        </div>
                        <p>Designed to make uncertainty visible before conviction gets comfortable.</p>
                    </div>
                    <div className="workflow-grid">
                        {WORKFLOW.map((step) => (
                            <article className="workflow-card" key={step.number}>
                                <div className="workflow-top"><span>{step.number}</span><Icon name={step.icon} size={18} /></div>
                                <h3>{step.title}</h3>
                                <p>{step.text}</p>
                            </article>
                        ))}
                    </div>
                </section>

                <div id="history"><RecentRuns /></div>
            </main>

            <footer className="site-footer shell">
                <div className="brand brand-footer"><span className="brand-mark"><Icon name="spark" size={14} /></span><span>trade<span>agents</span></span></div>
                <span>Research infrastructure for clearer decisions.</span>
                <a href="#new-run">Start a run <Icon name="arrowUpRight" size={14} /></a>
            </footer>
        </div>
    );
}
