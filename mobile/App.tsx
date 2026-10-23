import { useEffect, useState, type ReactNode } from "react"
import { Browser } from "@capacitor/browser"
import { Capacitor } from "@capacitor/core"

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "")
const USER_ID_KEY = "haven.mobile.userId"
const CHECKINS_KEY = "haven.mobile.checkins"
const AUTH_TOKEN_KEY = "haven.auth.token"
const AUTH_USER_KEY = "haven.auth.user"
type SavedCheckin = { mood: number; note: string; createdAt: string }
type HavenResource = { name: string; link: string }

function getUserId() {
  let id = localStorage.getItem(USER_ID_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(USER_ID_KEY, id)
  }
  return id
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  if (!API_BASE && Capacitor.isNativePlatform()) {
    throw new Error("The deployed Haven API URL is missing from this APK. Set the HAVEN_API_BASE_URL GitHub secret and rebuild.")
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(localStorage.getItem(AUTH_TOKEN_KEY) ? { Authorization: `Bearer ${localStorage.getItem(AUTH_TOKEN_KEY)}` } : {}), ...options?.headers },
  })
  if (!response.ok) throw new Error(`Haven couldn’t connect (${response.status}). Check your connection and try again.`)
  return response.json() as Promise<T>
}

function AuthGate({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("register")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const submit = async () => {
    setBusy(true); setError("")
    try {
      const result = await api<{token:string; user:{id:string;email:string;role:string}}>(`/api/auth/${mode}`, {method:"POST",body:JSON.stringify({email,password})})
      localStorage.setItem(AUTH_TOKEN_KEY,result.token); localStorage.setItem(AUTH_USER_KEY,JSON.stringify(result.user)); onAuthenticated()
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <div className="auth-gate"><div className="auth-card"><div className="wordmark"><span><Icon name="spark" size={15}/></span>haven</div><h1>{mode === "register" ? "Make space for you." : "Welcome back."}</h1><p>Your Safe Space chats stay temporary unless you choose to save them.</p><label>Email<input autoComplete="email" type="email" value={email} onChange={e=>setEmail(e.target.value)} /></label><label>Password<input autoComplete={mode === "register" ? "new-password" : "current-password"} type="password" value={password} onChange={e=>setPassword(e.target.value)} /></label>{error && <p role="alert">{error}</p>}<button className="app-button" onClick={submit} disabled={busy}>{busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}</button><button className="auth-switch" onClick={()=>setMode(mode === "register" ? "login" : "register")}>{mode === "register" ? "Already have an account? Sign in" : "New to Haven? Create an account"}</button><small>Use at least 12 characters for your password.</small></div></div>
}

function readCheckins(): SavedCheckin[] {
  try { return JSON.parse(localStorage.getItem(CHECKINS_KEY) || "[]") as SavedCheckin[] }
  catch { return [] }
}

function localDateInput(date: Date) {
  const adjusted = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return adjusted.toISOString().slice(0, 10)
}

type Tab = "home" | "checkins" | "resources" | "profile"
type Screen = Tab | "chat" | "counselors" | "resourceDetail" | "privacy" | "urgent" | "diary" | "saved"
type Sheet = "checkin" | "booking" | null
type IconName = "home" | "pulse" | "book" | "user" | "message" | "shield" | "lock" | "arrow" | "back" | "spark" | "calendar" | "clock" | "send" | "close" | "check" | "heart" | "external" | "leaf" | "bell" | "trash"

const iconPaths: Record<IconName, ReactNode> = {
  home: (
    <>
      <path d="m3 10 9-7 9 7" />
      <path d="M5.5 8.5V21h13V8.5M9 21v-7h6v7" />
    </>
  ),
  pulse: <path d="M3 12h4l2-7 4 14 2.5-7H21" />,
  book: (
    <>
      <path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H11v17H6.5A2.5 2.5 0 0 0 4 21.5Z" />
      <path d="M20 4.5A2.5 2.5 0 0 0 17.5 2H13v17h4.5a2.5 2.5 0 0 1 2.5 2.5Z" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 21a7.5 7.5 0 0 1 15 0" />
    </>
  ),
  message: (
    <path d="M21 11.5a8.4 8.4 0 0 1-9 8.5 9.8 9.8 0 0 1-4-.9L3 21l1.8-4.5A8.4 8.4 0 1 1 21 11.5Z" />
  ),
  shield: (
    <>
      <path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" />
      <path d="m9 12 2 2 4-5" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="10" width="14" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </>
  ),
  arrow: (
    <>
      <path d="M4 12h15M14 6l6 6-6 6" />
    </>
  ),
  back: <path d="m15 18-6-6 6-6" />,
  spark: (
    <>
      <path d="m12 3 1.6 5.3L19 10l-5.4 1.7L12 17l-1.6-5.3L5 10l5.4-1.7L12 3Z" />
      <path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2.5" />
      <path d="M8 3v4M16 3v4M3 10h18" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </>
  ),
  send: (
    <>
      <path d="m22 2-7 20-4-9-9-4Z" />
      <path d="M22 2 11 13" />
    </>
  ),
  close: <path d="m6 6 12 12M18 6 6 18" />,
  check: <path d="m5 12 4 4L19 6" />,
  heart: (
    <path d="M20.8 5.8a5.5 5.5 0 0 0-7.8 0L12 6.9l-1.1-1.1a5.5 5.5 0 0 0-7.7 7.8L12 22l8.8-8.4a5.5 5.5 0 0 0 0-7.8Z" />
  ),
  external: (
    <>
      <path d="M14 4h6v6M20 4l-9 9" />
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    </>
  ),
  leaf: (
    <>
      <path d="M20.5 3.5C13 3.5 6 7 5 14c-.6 4 2 6 5 6 7 0 10.5-8 10.5-16.5Z" />
      <path d="M4 21c2-5 6-9 12-12" />
    </>
  ),
  bell: (
    <>
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
    </>
  ),
  trash: (
    <>
      <path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14" />
    </>
  ),
}

function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {iconPaths[name]}
    </svg>
  )
}

const tabs: { id: Tab; label: string; icon: IconName }[] = [
  { id: "home", label: "Home", icon: "home" },
  { id: "checkins", label: "Check-ins", icon: "pulse" },
  { id: "resources", label: "Resources", icon: "book" },
  { id: "profile", label: "Profile", icon: "user" },
]

const resources = [
  {
    topic: "Anxiety",
    title: "Come back to this moment",
    time: "4 min",
    color: "mint",
    icon: "leaf" as IconName,
  },
  {
    topic: "Sleep",
    title: "A softer end to the day",
    time: "6 min",
    color: "lilac",
    icon: "spark" as IconName,
  },
  {
    topic: "Stress",
    title: "Make room for one slow breath",
    time: "3 min",
    color: "peach",
    icon: "heart" as IconName,
  },
]

function AppButton({
  children,
  onClick,
  secondary = false,
  icon,
}: {
  children: ReactNode
  onClick?: () => void
  secondary?: boolean
  icon?: IconName
}) {
  return (
    <button
      className={`app-button ${secondary ? "app-button--secondary" : ""}`}
      onClick={onClick}
    >
      <span>{children}</span>
      {icon && <Icon name={icon} size={18} />}
    </button>
  )
}

function Header({
  title,
  back,
  action,
}: {
  title?: string
  back?: () => void
  action?: ReactNode
}) {
  return (
    <header className="app-header">
      <div>
        {back && (
          <button className="round-button" onClick={back} aria-label="Go back">
            <Icon name="back" />
          </button>
        )}
      </div>
      {title ? (
        <strong>{title}</strong>
      ) : (
        <div className="wordmark">
          <span>
            <Icon name="spark" size={15} />
          </span>
          haven
        </div>
      )}
      <div>{action}</div>
    </header>
  )
}

function BottomNav({ active, go }: { active: Tab; go: (tab: Tab) => void }) {
  return (
    <nav className="bottom-nav">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={active === tab.id ? "active" : ""}
          onClick={() => go(tab.id)}
        >
          <span>
            <Icon name={tab.icon} size={21} />
          </span>
          <small>{tab.label}</small>
        </button>
      ))}
    </nav>
  )
}

function Home({
  go,
  open,
}: {
  go: (screen: Screen) => void
  open: (sheet: Sheet) => void
}) {
  return (
    <div className="screen screen--home">
      <Header
        action={
          <button className="avatar-button" onClick={() => go("profile")}>
            A
          </button>
        }
      />
      <main className="screen-scroll">
        <section className="greeting">
          <div>
            <span>GOOD AFTERNOON</span>
            <h1>
              How are you,
              <br />
              <em>really?</em>
            </h1>
          </div>
          <button className="notification-button" aria-label="Notifications">
            <Icon name="bell" size={19} />
            <i />
          </button>
        </section>

        <button className="safe-space" onClick={() => go("chat")}>
          <div className="safe-space-glow" />
          <div className="safe-orbit safe-orbit--one" />
          <div className="safe-orbit safe-orbit--two" />
          <div className="safe-space-top">
            <span className="live-dot">
              <i />
              SAFE SPACE IS READY
            </span>
            <span className="safe-icon">
              <Icon name="message" size={23} />
            </span>
          </div>
          <div className="safe-space-copy">
            <h2>
              A quiet place to
              <br />
              say what’s on your mind.
            </h2>
            <p>
              <Icon name="lock" size={14} />
              This conversation won’t be saved
            </p>
          </div>
          <span className="safe-space-action">
            Start talking <Icon name="arrow" size={17} />
          </span>
        </button>

        <section className="quick-section">
          <div className="section-title">
            <div>
              <span>FOR THIS MOMENT</span>
              <h2>What would feel helpful?</h2>
            </div>
            <i />
          </div>
          <div className="quick-grid">
            <button
              className="quick-card quick-card--checkin"
              onClick={() => open("checkin")}
            >
              <span className="quick-icon">
                <Icon name="pulse" />
              </span>
              <div className="mood-preview">
                <i />
                <i />
                <i className="active" />
                <i />
                <i />
              </div>
              <div>
                <strong>Check in</strong>
                <small>Notice how you feel</small>
              </div>
            </button>
            <button
              className="quick-card quick-card--counselor"
              onClick={() => go("counselors")}
            >
              <span className="quick-icon">
                <Icon name="user" />
              </span>
              <div className="people-preview">
                <i>AM</i>
                <i>JR</i>
                <i>SK</i>
              </div>
              <div>
                <strong>Find a counselor</strong>
                <small>Connect with support</small>
              </div>
            </button>
          </div>
        </section>

        <section className="resource-teaser">
          <div className="section-title">
            <div>
              <span>TAKE A SMALL PAUSE</span>
              <h2>Something gentle for today</h2>
            </div>
            <button onClick={() => go("resources")}>See all</button>
          </div>
          <button
            className="featured-resource"
            onClick={() => go("resources")}
          >
            <div className="resource-illustration">
              <div className="sun" />
              <div className="hill hill--one" />
              <div className="hill hill--two" />
              <span>
                <Icon name="leaf" size={21} />
              </span>
            </div>
            <div className="featured-copy">
              <span>STRESS · 4 MIN</span>
              <h3>Come back to this moment</h3>
              <p>
                A grounding practice for when everything feels like too much.
              </p>
              <div>
                Browse resources <Icon name="arrow" size={16} />
              </div>
            </div>
          </button>
        </section>

        <button className="urgent-bar" onClick={() => go("urgent")}>
          <span>
            <Icon name="heart" size={18} />
          </span>
          <div>
            <strong>Need support right now?</strong>
            <small>Find immediate help options</small>
          </div>
          <Icon name="arrow" size={17} />
        </button>
      </main>
      <BottomNav active="home" go={go} />
    </div>
  )
}

function Checkins({
  go,
  open,
  entries,
}: {
  go: (screen: Screen) => void
  open: (sheet: Sheet) => void
  entries: SavedCheckin[]
}) {
  const weekStart = new Date()
  weekStart.setHours(0, 0, 0, 0)
  weekStart.setDate(weekStart.getDate() - ((weekStart.getDay() + 6) % 7))
  const today = new Date()
  const chartDays = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(weekStart)
    date.setDate(date.getDate() + index)
    const match = entries.find((entry) => new Date(entry.createdAt).toDateString() === date.toDateString())
    return { label: new Intl.DateTimeFormat(undefined, { weekday: "narrow" }).format(date), height: match ? match.mood * 20 : 0, selected: date.toDateString() === today.toDateString() }
  })
  const weekEnd = new Date(weekStart)
  weekEnd.setDate(weekEnd.getDate() + 6)
  return (
    <div className="screen">
      <Header
        title="Check-ins"
        action={
          <button
            className="header-text-button"
            onClick={() => open("checkin")}
          >
            New
          </button>
        }
      />
      <main className="screen-scroll">
        <section className="page-heading">
          <span>YOUR PRIVATE REFLECTIONS</span>
          <h1>
            A week in
            <br />
            <em>small moments.</em>
          </h1>
          <p>These are the check-ins you chose to save.</p>
        </section>
        <section className="rhythm-card">
          <div className="rhythm-top">
            <div>
              <span>THIS WEEK · YOUR DEVICE</span>
              <strong>{weekStart.toLocaleDateString(undefined, { month: "short", day: "numeric" })}–{weekEnd.toLocaleDateString(undefined, { month: "short", day: "numeric" })}</strong>
            </div>
            <span className="private-pill">
              <Icon name="lock" size={12} />
              Private
            </span>
          </div>
          <div className="rhythm-chart">
            {chartDays.map((item, index) => (
              <div key={index} className={item.selected ? "selected" : ""}>
                <span style={{ height: `${item.height}%` }} />
                <small>{item.label}</small>
              </div>
            ))}
          </div>
          <p>
            Check-ins help you reflect. They aren’t a diagnosis or medical
            assessment.
          </p>
        </section>
        <div className="section-title recent-title">
          <div>
            <span>RECENT</span>
            <h2>Your saved check-ins</h2>
          </div>
        </div>
        <section className="checkin-list">
          {entries.length ? entries.map((entry) => {
            const mood = ["", "Very low", "Low", "Okay", "Good", "Great"][entry.mood]
            return <article key={entry.createdAt}>
              <span className={`score score--${entry.mood}`}>{entry.mood}</span>
              <div>
                <strong>{mood}</strong>
                <small>{new Date(entry.createdAt).toLocaleString()}</small>
                {entry.note && <small>{entry.note}</small>}
              </div>
            </article>
          }) : <p className="empty-checkins">Your saved check-ins will appear here.</p>}
        </section>
        <button className="manage-data" onClick={() => go("privacy")}>
          <Icon name="shield" size={18} />
          Manage your saved data
          <Icon name="arrow" size={16} />
        </button>
      </main>
      <BottomNav active="checkins" go={go} />
    </div>
  )
}

function Resources({ go, choose }: { go: (screen: Screen) => void; choose: (resource: HavenResource) => void }) {
  const [filter, setFilter] = useState("All")
  const [items, setItems] = useState<HavenResource[]>([])
  const [error, setError] = useState("")
  useEffect(() => { api<HavenResource[]>("/api/resources").then(setItems).catch((e: Error) => setError(e.message)) }, [])
  const filters = ["All", ...new Set(items.map((item) => item.name))]
  return (
    <div className="screen">
      <Header
        title="Resources"
        action={
          <button className="round-button">
            <Icon name="book" size={18} />
          </button>
        }
      />
      <main className="screen-scroll">
        <section className="page-heading page-heading--compact">
          <span>EXPLORE AT YOUR OWN PACE</span>
          <h1>
            What would feel
            <br />
            <em>helpful today?</em>
          </h1>
        </section>
        <label className="search-field">
          <Icon name="spark" size={18} />
          <input
            aria-label="Search resources"
            placeholder="Search a feeling or topic"
          />
        </label>
        <div className="filter-scroll">
          {filters.map((item) => (
            <button
              key={item}
              className={filter === item ? "active" : ""}
              onClick={() => setFilter(item)}
            >
              {item}
            </button>
          ))}
        </div>
        <section className="resource-list">
          {items
            .filter((item) => filter === "All" || item.name === filter)
            .map((item) => (
              <button
                className="resource-row"
                key={item.name}
                onClick={() => { choose(item); go("resourceDetail") }}
              >
                <div className="resource-row-art">
                  <Icon name="book" size={23} />
                  <i />
                  <i />
                </div>
                <div>
                  <span>
                    {item.name.toUpperCase()} · EXTERNAL RESOURCE
                  </span>
                  <h3>Support and information about {item.name.toLowerCase()}</h3>
                  <p>Guidance from a trusted mental health resource.</p>
                  <small>
                    Open resource <Icon name="arrow" size={14} />
                  </small>
                </div>
              </button>
            ))}
          {error && <p role="alert">{error}</p>}
          {!error && !items.length && <p>Loading resources…</p>}
        </section>
        <button
          className="urgent-bar urgent-bar--resources"
          onClick={() => go("urgent")}
        >
          <span>
            <Icon name="heart" size={18} />
          </span>
          <div>
            <strong>Need help right now?</strong>
            <small>View urgent support options</small>
          </div>
          <Icon name="arrow" size={17} />
        </button>
      </main>
      <BottomNav active="resources" go={go} />
    </div>
  )
}

function ResourceDetail({ go, resource }: { go: (screen: Screen) => void; resource: HavenResource | null }) {
  return (
    <div className="screen detail-screen">
      <Header title="Resource" back={() => go("resources")} />
      <main className="screen-scroll">
        <div className="detail-art">
          <div className="detail-sun" />
          <i />
          <i />
          <span>
            <Icon name="leaf" size={27} />
          </span>
        </div>
        <div className="detail-copy">
          <span>{resource?.name.toUpperCase() || "HAVEN RESOURCE"}</span>
          <h1>
            Find support
            <br />
            <em>and information.</em>
          </h1>
          <p>
            Explore information and support from a trusted mental health organization.
          </p>
        </div>
        <div className="external-note">
          <Icon name="external" size={17} />
          <p>
            This resource opens on an independent mental health website with its
            own privacy policy.
          </p>
        </div>
        <AppButton icon="external" onClick={() => resource?.link && Browser.open({ url: resource.link })}>Open full resource</AppButton>
      </main>
    </div>
  )
}

function Counselors({
  go,
  open,
}: {
  go: (screen: Screen) => void
  open: (sheet: Sheet, counselor?: string) => void
}) {
  return (
    <div className="screen">
      <Header title="Find a counselor" back={() => go("home")} />
      <main className="screen-scroll">
        <section className="page-heading page-heading--compact">
          <span>CONNECT WITH SUPPORT</span>
          <h1>
            Have a counselor
            <br />
            <em>in mind?</em>
          </h1>
          <p>
            Haven can record a requested time, but it cannot contact or confirm with a counselor yet.
          </p>
        </section>
        <section className="counselor-list">
            <article className="counselor-row counselor-row--sage">
              <div className="counselor-avatar">
                <span>HC</span>
                <i />
                <i />
              </div>
              <div className="counselor-copy">
                <span>APPOINTMENT REQUEST</span>
                <h3>Your counselor</h3>
                <p>Enter the counselor’s name when you request a time. Haven stores the request but does not send it to them.</p>
                <small>
                  <Icon name="calendar" size={14} />
                  You’ll need to follow up with them directly
                </small>
                <AppButton
                  secondary
                  icon="arrow"
                  onClick={() => open("booking", "")}
                >
                  Record a requested time
                </AppButton>
              </div>
            </article>
        </section>
      </main>
    </div>
  )
}

function Profile({ go, onLock, onSignOut }: { go: (screen: Screen) => void; onLock: () => void; onSignOut: () => void }) {
  const account = JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "{}") as {email?:string}
  return (
    <div className="screen">
      <Header title="Profile" />
      <main className="screen-scroll">
        <section className="profile-card">
          <div className="profile-avatar">A</div>
          <div>
            <span>YOUR SPACE</span>
            <h1>{account.email || "Your Haven"}</h1>
            <p>Settings, privacy, and support</p>
          </div>
        </section>
        <button className="privacy-card" onClick={() => go("privacy")}>
          <span>
            <Icon name="shield" size={24} />
          </span>
          <div>
            <strong>Your privacy at a glance</strong>
            <p>
              Chats aren’t saved. Check-ins and appointments are saved only when
              you choose those features.
            </p>
            <small>
              Review privacy details <Icon name="arrow" size={14} />
            </small>
          </div>
        </button>
        <section className="settings">
          <h2>Your data</h2>
          <button onClick={() => go("diary")}><span><Icon name="book" /></span><div><strong>Private diary</strong><small>Write, edit, and delete private entries</small></div><Icon name="arrow" size={16} /></button>
          <button onClick={() => go("saved")}><span><Icon name="message" /></span><div><strong>Saved conversations</strong><small>Only conversations you chose to save</small></div><Icon name="arrow" size={16} /></button>
          <button onClick={() => go("checkins")}>
            <span>
              <Icon name="pulse" />
            </span>
            <div>
              <strong>Manage check-ins</strong>
              <small>Review check-ins saved on this device</small>
            </div>
            <Icon name="arrow" size={16} />
          </button>
          <button onClick={() => go("counselors")}>
            <span>
              <Icon name="calendar" />
            </span>
            <div>
              <strong>Request an appointment</strong>
              <small>Haven records requests but doesn’t send them</small>
            </div>
            <Icon name="arrow" size={16} />
          </button>
        </section>
        <section className="settings">
          <h2>Settings & help</h2>
          <button onClick={onLock}><span><Icon name="lock" /></span><div><strong>Lock Haven</strong><small>Lock now; automatically locks after 5 minutes away</small></div><Icon name="arrow" size={16} /></button>
          <button onClick={onSignOut}><span><Icon name="back" /></span><div><strong>Sign out</strong><small>End this account session on this device</small></div><Icon name="arrow" size={16} /></button>
          <button onClick={() => go("privacy")}>
            <span>
              <Icon name="lock" />
            </span>
            <div>
              <strong>Privacy settings</strong>
            </div>
            <Icon name="arrow" size={16} />
          </button>
          <button onClick={() => go("urgent")}>
            <span>
              <Icon name="heart" />
            </span>
            <div>
              <strong>Urgent support</strong>
            </div>
            <Icon name="arrow" size={16} />
          </button>
        </section>
        <p className="version">Haven · Version 1.0</p>
      </main>
      <BottomNav active="profile" go={go} />
    </div>
  )
}

function Privacy({ go }: { go: (screen: Screen) => void }) {
  return (
    <div className="screen">
      <Header title="Privacy" back={() => go("profile")} />
      <main className="screen-scroll">
        <section className="privacy-hero">
          <span>
            <Icon name="shield" size={31} />
          </span>
          <h1>
            You’re in control
            <br />
            <em>of what stays.</em>
          </h1>
          <p>No fine-print maze. Here’s exactly how your information works.</p>
        </section>
        <section className="privacy-list">
          {[
            [
              "message",
              "NOT SAVED",
              "Safe Space chats",
              "Messages clear when you end the chat. There’s no conversation history.",
            ],
            [
              "pulse",
              "SAVED WHEN YOU CHOOSE",
              "Daily check-ins",
              "Mood and notes are sent to Haven when you tap Save check-in; a copy stays on this device.",
            ],
            [
              "calendar",
              "SAVED WHEN SUBMITTED",
              "Appointment requests",
              "Counselor name, requested date, and time are saved. Haven does not send or confirm the request.",
            ],
          ].map(([icon, label, title, text]) => (
            <article key={title}>
              <span>
                <Icon name={icon as IconName} />
              </span>
              <div>
                <small>{label}</small>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </article>
          ))}
        </section>
        <div className="delete-data">
          <Icon name="trash" size={18} />
          <span>To clear this device’s history, clear Haven app storage in Android settings. Backend check-ins cannot be deleted from the app yet.</span>
        </div>
      </main>
    </div>
  )
}

function Urgent({ go }: { go: (screen: Screen) => void }) {
  return (
    <div className="screen urgent-screen">
      <Header title="Urgent support" back={() => go("home")} />
      <main className="screen-scroll">
        <section className="urgent-hero">
          <span>
            <Icon name="heart" size={27} />
          </span>
          <h1>
            You deserve support
            <br />
            <em>right now.</em>
          </h1>
          <p>
            If you may be in immediate danger or might hurt yourself or someone
            else, contact local emergency services now.
          </p>
        </section>
        <section className="urgent-options">
          <article>
            <span>IMMEDIATE DANGER</span>
            <h3>Contact local emergency services</h3>
            <p>
              Use your device’s emergency call feature or go to the nearest
              emergency department.
            </p>
            <p>Use your device’s emergency feature to contact local services.</p>
          </article>
          <article>
            <span>CRISIS SUPPORT</span>
            <h3>Talk with a crisis counselor</h3>
            <p>
              Verified local support options will appear here when configured.
            </p>
            <p>Verified local crisis contacts haven’t been configured yet.</p>
          </article>
        </section>
        <div className="unconfigured">
          <Icon name="shield" size={18} />
          <div>
            <strong>Local contacts aren’t configured yet</strong>
            <p>Haven will show verified options for your region here.</p>
          </div>
        </div>
        <p className="urgent-disclaimer">
          Haven does not monitor messages or provide emergency services.
        </p>
      </main>
    </div>
  )
}

function Chat({ go, initialMessages = [] }: { go: (screen: Screen) => void; initialMessages?: { role: "user" | "haven"; text: string }[] }) {
  const [messages, setMessages] = useState<{ role: "user" | "haven"; text: string }[]>(initialMessages)
  const [input, setInput] = useState("")
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState("")
  const [saved, setSaved] = useState(false)
  const send = async () => {
    if (!input.trim()) return
    const message = input.trim()
    setMessages((current) => [...current, { role: "user", text: message }])
    setInput("")
    setThinking(true)
    setError("")
    try {
      const data = await api<{ response: string }>("/api/chat", { method: "POST", body: JSON.stringify({ message }) })
      setMessages((current) => [...current, { role: "haven", text: data.response }])
    } catch (e) { setError((e as Error).message) }
    finally { setThinking(false) }
  }
  return (
    <div className="screen chat-screen">
      <Header
        title="Safe Space"
        back={() => go("home")}
        action={
          <button
            className="header-text-button header-text-button--warm"
            onClick={() => go("home")}
          >
            End
          </button>
        }
      />
      <div className="chat-privacy">
        <Icon name="lock" size={13} />
        Private moment · This conversation isn’t saved
        {!!messages.length && <button className="chat-save" disabled={saved} onClick={async () => { try { await api("/api/conversations", { method:"POST", body:JSON.stringify({ title:"Safe Space conversation", messages }) }); setSaved(true) } catch(e) { setError((e as Error).message) } }}>{saved ? "Saved" : "Save chat"}</button>}
      </div>
      <main className="chat-scroll">
        <section className="chat-intro">
          <span>
            <Icon name="spark" size={23} />
          </span>
          <h2>I’m here with you.</h2>
          <p>Share as much or as little as feels right.</p>
        </section>
        <div className="haven-bubble">
          What feels most present for you right now?
        </div>
        {messages.map((message, index) => (
          <div className={message.role === "user" ? "my-bubble" : "haven-bubble"} key={`${message.text}-${index}`}>
            {message.text}
          </div>
        ))}
        {error && <p role="alert">{error}</p>}
        {thinking && (
          <div className="haven-bubble typing-bubble">
            <i />
            <i />
            <i />
          </div>
        )}
        {!messages.length && (
          <div className="prompt-chips">
            {[
              "Something is weighing on me",
              "I need help slowing down",
              "I’m not sure where to start",
            ].map((prompt) => (
              <button onClick={() => setInput(prompt)} key={prompt}>
                {prompt}
                <Icon name="arrow" size={14} />
              </button>
            ))}
          </div>
        )}
      </main>
      <footer className="composer">
        <div>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && send()}
            placeholder="Share what’s on your mind…"
          />
          <button onClick={send} aria-label="Send message">
            <Icon name="send" size={18} />
          </button>
        </div>
        <p>Haven offers support, but does not replace professional care.</p>
      </footer>
    </div>
  )
}

type DiaryRecord = { id: string; title: string; content: string; mood: string | null; updated_at: string }
function Diary({ go }: { go: (screen: Screen) => void }) {
  const [items, setItems] = useState<DiaryRecord[]>([])
  const [content, setContent] = useState("")
  const [title, setTitle] = useState("")
  const [editing, setEditing] = useState<string | null>(null)
  const [error, setError] = useState("")
  const refresh = () => api<DiaryRecord[]>("/api/diary").then(setItems).catch(e => setError((e as Error).message))
  useEffect(() => { refresh() }, [])
  const save = async () => { if (!content.trim()) return; try { if(editing)await api(`/api/diary/${editing}`,{method:"PATCH",body:JSON.stringify({title,content})});else await api("/api/diary", {method:"POST",body:JSON.stringify({title,content})}); setEditing(null);setTitle("");setContent("");refresh() } catch(e) {setError((e as Error).message)} }
  const remove = async (id: string) => { try { await api(`/api/diary/${id}`,{method:"DELETE"});refresh() } catch(e) {setError((e as Error).message)} }
  return <div className="screen"><Header title="Private diary" back={()=>go("profile")}/><main className="screen-scroll"><section className="page-heading"><span>ONLY YOU CAN SEE THESE</span><h1>Your own<br/><em>quiet page.</em></h1><p>Entries are private to your account and never added to Haven’s monitoring.</p></section><label className="note-field"><span>Title <small>Optional</small></span><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="A note to yourself"/></label><label className="note-field diary-editor"><span>Write freely</span><textarea rows={6} value={content} onChange={e=>setContent(e.target.value)} placeholder="What would you like to remember?"/></label><AppButton onClick={save}>{editing?"Update entry":"Save entry"}</AppButton>{editing&&<button className="auth-switch" onClick={()=>{setEditing(null);setTitle("");setContent("")}}>Cancel edit</button>}{error&&<p role="alert">{error}</p>}<section className="checkin-list">{items.map(item=><article key={item.id}><div><strong>{item.title||"Untitled entry"}</strong><small>{new Date(item.updated_at).toLocaleString()}</small><small>{item.content}</small><button className="header-text-button" onClick={()=>{setEditing(item.id);setTitle(item.title);setContent(item.content)}}>Edit entry</button></div><button aria-label="Delete entry" onClick={()=>remove(item.id)}><Icon name="trash" size={17}/></button></article>)}</section></main></div>
}

type ConversationSummary = {id:string;title:string;updated_at:string}
function SavedChats({ go, onOpen }: { go:(screen:Screen)=>void; onOpen:(id:string)=>void }) {
 const [items,setItems]=useState<ConversationSummary[]>([]); const [error,setError]=useState("")
 const refresh=()=>api<ConversationSummary[]>("/api/conversations").then(setItems).catch(e=>setError((e as Error).message)); useEffect(()=>{refresh()},[])
 const remove=async(id:string)=>{await api(`/api/conversations/${id}`,{method:"DELETE"});refresh()}
 return <div className="screen"><Header title="Saved conversations" back={()=>go("profile")}/><main className="screen-scroll"><section className="page-heading"><span>SAVED BY YOU</span><h1>Your words,<br/><em>when you need them.</em></h1><p>Only chats you explicitly save appear here.</p></section>{error&&<p role="alert">{error}</p>}<section className="checkin-list">{items.map(item=><article key={item.id}><div><strong>{item.title}</strong><small>{new Date(item.updated_at).toLocaleString()}</small><button className="header-text-button" onClick={()=>onOpen(item.id)}>Open conversation</button></div><button aria-label="Delete conversation" onClick={()=>remove(item.id)}><Icon name="trash" size={17}/></button></article>)}{!items.length&&!error&&<p className="empty-checkins">No saved conversations yet.</p>}</section></main></div>
}

function CheckinSheet({ close, onSaved }: { close: () => void; onSaved: (entry: SavedCheckin) => void }) {
  const [mood, setMood] = useState(3)
  const [saved, setSaved] = useState(false)
  const [note, setNote] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const save = async () => {
    const entry = { mood, note: note.trim(), createdAt: new Date().toISOString() }
    const moodName = ["", "Very low", "Low", "Okay", "Good", "Great"][mood]
    setSaving(true)
    setError("")
    try {
      await api<{ response: string }>("/api/checkin", {
        method: "POST",
        body: JSON.stringify({ user_id: getUserId(), message: `Mood: ${moodName} (${mood}/5)${entry.note ? `\\nNote: ${entry.note}` : ""}` }),
      })
      onSaved(entry)
      setSaved(true)
    } catch (e) { setError((e as Error).message) }
    finally { setSaving(false) }
  }
  return (
    <div
      className="sheet-backdrop"
      onMouseDown={(event) => event.target === event.currentTarget && close()}
    >
      <section className="sheet">
        <div className="sheet-handle" />
        <button className="sheet-close" onClick={close} aria-label="Close">
          <Icon name="close" size={19} />
        </button>
        {saved ? (
          <div className="sheet-success">
            <span>
              <Icon name="check" size={29} />
            </span>
            <small>CHECK-IN SAVED</small>
            <h2>
              Thanks for taking
              <br />a moment.
            </h2>
            <p>Your check-in is now in your private history.</p>
            <AppButton onClick={close}>Done</AppButton>
          </div>
        ) : (
          <>
            <div className="sheet-label">A MOMENT FOR YOU</div>
            <h2>
              How are you feeling
              <br />
              <em>right now?</em>
            </h2>
            <p className="sheet-lead">
              There’s no right answer. Choose what feels closest.
            </p>
            <div className="mood-picker">
              {["Very low", "Low", "Okay", "Good", "Great"].map(
                (label, index) => (
                  <button
                    className={mood === index + 1 ? "active" : ""}
                    key={label}
                    onClick={() => setMood(index + 1)}
                  >
                    <span>{index + 1}</span>
                    <small>{label}</small>
                  </button>
                ),
              )}
            </div>
            <label className="note-field">
              <span>
                Add a note <small>Optional</small>
              </span>
              <textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} placeholder="What’s on your mind today?" />
            </label>
            <div className="save-note">
              <Icon name="lock" size={15} />
              Saving adds this to your private check-in history.
            </div>
            {error && <p role="alert">{error}</p>}
            <AppButton onClick={save}>{saving ? "Saving…" : "Save check-in"}</AppButton>
          </>
        )}
      </section>
    </div>
  )
}

function BookingSheet({ close }: { close: () => void }) {
  const [step, setStep] = useState(1)
  const [counselor, setCounselor] = useState("")
  const [date, setDate] = useState(() => { const d = new Date(); d.setDate(d.getDate() + 2); return localDateInput(d) })
  const [time, setTime] = useState("13:00")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const submit = async () => {
    setSaving(true); setError("")
    try {
      await api<{ message: string }>("/api/appointment", { method: "POST", body: JSON.stringify({ user_id: getUserId(), counselor: counselor.trim(), time: `${date} ${time}` }) })
      setStep(3)
    } catch (e) { setError((e as Error).message) }
    finally { setSaving(false) }
  }
  return (
    <div className="sheet-backdrop">
      <section className="sheet booking-sheet">
        <div className="sheet-handle" />
        <button className="sheet-close" onClick={close}>
          <Icon name="close" size={19} />
        </button>
        {step < 3 && (
          <div className="stepper">
            <i className="active" />
            <i className={step === 2 ? "active" : ""} />
          </div>
        )}
        {step === 1 && (
          <>
            <div className="sheet-label">REQUEST AN APPOINTMENT</div>
            <h2>Request a time<br /><em>with your counselor.</em></h2>
            <label className="note-field"><span>Counselor name</span><input value={counselor} onChange={(e) => setCounselor(e.target.value)} placeholder="Enter their name" /></label>
            <label className="note-field"><span>Requested date</span><input type="date" value={date} min={localDateInput(new Date())} onChange={(e) => setDate(e.target.value)} /></label>
            <label className="note-field"><span>Requested time</span><input type="time" value={time} onChange={(e) => setTime(e.target.value)} /></label>
            <p className="save-note">This records a request in Haven. It does not contact or book with the counselor.</p>
            {error && <p role="alert">{error}</p>}
            <AppButton onClick={() => counselor.trim() && date && time && setStep(2)} icon="arrow">
              Review request
            </AppButton>
          </>
        )}
        {step === 2 && (
          <>
            <div className="sheet-label">REVIEW REQUEST</div>
            <h2>
              Does everything
              <br />
              <em>look right?</em>
            </h2>
            <div className="booking-summary">
              <span>HC</span>
              <div>
                <strong>{counselor}</strong>
                <small>Requested counselor</small>
              </div>
              <hr />
              <p>
                <Icon name="calendar" size={18} />
                <span>
                  <small>DATE</small>
                  <strong>{new Date(`${date}T00:00:00`).toLocaleDateString()}</strong>
                </span>
              </p>
              <p>
                <Icon name="clock" size={18} />
                <span>
                  <small>TIME</small>
                  <strong>{time}</strong>
                </span>
              </p>
            </div>
            <div className="save-note">
              <Icon name="lock" size={15} />
              Haven stores this request. You’ll need to contact the counselor directly.
            </div>
            {error && <p role="alert">{error}</p>}
            <AppButton onClick={submit}>{saving ? "Saving…" : "Record request"}</AppButton>
          </>
        )}
        {step === 3 && (
          <div className="sheet-success">
            <span>
              <Icon name="calendar" size={27} />
            </span>
            <small>REQUEST SAVED</small>
            <h2>
              Your request is
              <br />
              on its way.
            </h2>
            <p>
              Your requested date and counselor are saved in Haven. Contact them directly to confirm.
            </p>
            <AppButton onClick={close}>Back to Haven</AppButton>
          </div>
        )}
      </section>
    </div>
  )
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("home")
  const [authenticated, setAuthenticated] = useState(Boolean(localStorage.getItem(AUTH_TOKEN_KEY)))
  const [locked, setLocked] = useState(false)
  const [sheet, setSheet] = useState<Sheet>(null)
  const [checkins, setCheckins] = useState<SavedCheckin[]>(readCheckins)
  const [selectedResource, setSelectedResource] = useState<HavenResource | null>(null)
  const [openedMessages, setOpenedMessages] = useState<{role:"user"|"haven";text:string}[]>([])

  useEffect(() => {
    if (!authenticated) return
    let timer = window.setTimeout(() => setLocked(true), 5 * 60 * 1000)
    const reset = () => { window.clearTimeout(timer); timer = window.setTimeout(() => setLocked(true), 5 * 60 * 1000) }
    const visibility = () => { if (document.hidden) setLocked(true); else reset() }
    window.addEventListener("pointerdown", reset); window.addEventListener("keydown", reset); document.addEventListener("visibilitychange", visibility)
    return () => { window.clearTimeout(timer); window.removeEventListener("pointerdown", reset); window.removeEventListener("keydown", reset); document.removeEventListener("visibilitychange", visibility) }
  }, [authenticated])

  useEffect(() => {
    const splash = document.getElementById("boot-splash")
    const fade = window.setTimeout(() => splash?.classList.add("hide"), 650)
    const remove = window.setTimeout(() => splash?.remove(), 950)
    return () => { window.clearTimeout(fade); window.clearTimeout(remove) }
  }, [])

  const openSheet = (next: Sheet) => setSheet(next)
  const saveCheckin = (entry: SavedCheckin) => {
    const next = [entry, ...readCheckins()]
    localStorage.setItem(CHECKINS_KEY, JSON.stringify(next))
    setCheckins(next)
  }

  useEffect(() => {
    document.body.style.overflow = sheet ? "hidden" : ""
    return () => {
      document.body.style.overflow = ""
    }
  }, [sheet])

  const go = (next: Screen) => {
    if (next === "chat") setOpenedMessages([])
    setScreen(next)
    document.querySelector(".screen-scroll")?.scrollTo({ top: 0 })
  }

  if (!authenticated) return <AuthGate onAuthenticated={() => setAuthenticated(true)} />
  if (locked) return <PinGate onUnlock={() => setLocked(false)} onSignOut={() => { localStorage.removeItem(AUTH_TOKEN_KEY); localStorage.removeItem(AUTH_USER_KEY); localStorage.removeItem("haven.lock.pin"); setLocked(false); setAuthenticated(false) }} />

  return (
    <div className="app-stage">
      <div className="app-shell">
        <div key={screen} className="screen-transition">
          {screen === "home" && <Home go={go} open={openSheet} />}
          {screen === "checkins" && <Checkins go={go} open={openSheet} entries={checkins} />}
          {screen === "resources" && <Resources go={go} choose={setSelectedResource} />}
          {screen === "profile" && <Profile go={go} onLock={() => setLocked(true)} onSignOut={async () => { try { await api("/api/auth/logout",{method:"POST"}) } catch {} localStorage.removeItem(AUTH_TOKEN_KEY);localStorage.removeItem(AUTH_USER_KEY);localStorage.removeItem("haven.lock.pin");setAuthenticated(false) }} />}
          {screen === "chat" && <Chat go={go} initialMessages={openedMessages} />}
          {screen === "counselors" && <Counselors go={go} open={openSheet} />}
          {screen === "resourceDetail" && <ResourceDetail go={go} resource={selectedResource} />}
          {screen === "privacy" && <Privacy go={go} />}
          {screen === "urgent" && <Urgent go={go} />}
          {screen === "diary" && <Diary go={go} />}
          {screen === "saved" && <SavedChats go={go} onOpen={async id=>{try{const data=await api<{messages:{role:"user"|"haven";content:string}[]}>(`/api/conversations/${id}`);go("chat");setOpenedMessages(data.messages.map(m=>({role:m.role,text:m.content})))}catch(e){window.alert((e as Error).message)}}} />}
        </div>
        {sheet === "checkin" && <CheckinSheet close={() => setSheet(null)} onSaved={saveCheckin} />}
        {sheet === "booking" && <BookingSheet close={() => setSheet(null)} />}
      </div>
    </div>
  )
}

function PinGate({ onUnlock, onSignOut }: { onUnlock:()=>void; onSignOut:()=>void }) {
 const [pin,setPin]=useState(""); const [error,setError]=useState(""); const [busy,setBusy]=useState(false)
 const stored=localStorage.getItem("haven.lock.pin")
 const submit=async()=>{
  setBusy(true);setError("")
  if(!/^\d{6}$/.test(pin)){setError("Enter your 6-digit PIN.");setBusy(false);return}
  try{if(stored){await api("/api/security/pin/verify",{method:"POST",body:JSON.stringify({pin})});const [saltHex,expected]=stored.split(".");const salt=new Uint8Array(saltHex.match(/.{2}/g)!.map(x=>parseInt(x,16)));const key=await crypto.subtle.importKey("raw",new TextEncoder().encode(pin),"PBKDF2",false,["deriveBits"]);const bits=await crypto.subtle.deriveBits({name:"PBKDF2",salt,iterations:120000,hash:"SHA-256"},key,256);const actual=Array.from(new Uint8Array(bits),x=>x.toString(16).padStart(2,"0")).join("");if(actual!==expected)throw new Error("PIN verifier mismatch");onUnlock()}else{await api("/api/security/pin",{method:"PUT",body:JSON.stringify({pin})});const salt=crypto.getRandomValues(new Uint8Array(16));const encoded=Array.from(salt,x=>x.toString(16).padStart(2,"0")).join("");const key=await crypto.subtle.importKey("raw",new TextEncoder().encode(pin),"PBKDF2",false,["deriveBits"]);const bits=await crypto.subtle.deriveBits({name:"PBKDF2",salt,iterations:120000,hash:"SHA-256"},key,256);localStorage.setItem("haven.lock.pin",`${encoded}.${Array.from(new Uint8Array(bits),x=>x.toString(16).padStart(2,"0")).join("")}`);onUnlock()}}catch(e){setError((e as Error).message.includes("PIN")?"That PIN didn’t match, or hasn’t been set for this account.":"Could not verify your PIN. Reconnect and try again.")}finally{setBusy(false)}
 }
 return <div className="auth-gate"><div className="auth-card"><div className="wordmark"><span><Icon name="lock" size={15}/></span>haven</div><h1>{stored?"Haven is locked.":"Set your Haven PIN."}</h1><p>{stored?"Enter your 6-digit PIN to continue.":"Create a six-digit PIN for this device. It is stored as a salted verifier."}</p><label>6-digit PIN<input inputMode="numeric" type="password" maxLength={6} value={pin} onChange={e=>setPin(e.target.value.replace(/\D/g,""))}/></label>{error&&<p role="alert">{error}</p>}<button className="app-button" onClick={submit} disabled={busy}>{busy?"Checking…":stored?"Unlock Haven":"Set PIN and continue"}</button><button className="auth-switch" onClick={onSignOut}>Sign out instead</button><small>Your account remains protected by sign-in even if this device lock is cleared.</small></div></div>
}
