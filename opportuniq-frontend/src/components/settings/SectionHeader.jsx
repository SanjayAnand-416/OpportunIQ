export default function SectionHeader({ title, subtitle }) {
  return (
    <header className="settings-page-header">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </header>
  )
}
