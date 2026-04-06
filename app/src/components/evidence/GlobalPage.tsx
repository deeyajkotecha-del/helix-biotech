import { useNavigate } from 'react-router-dom'
import RegionalPanel from './RegionalPanel'

export default function GlobalPage() {
  const navigate = useNavigate()

  const handleAlertClick = (query: string) => {
    navigate(`/?q=${encodeURIComponent(query)}`)
  }

  return (
    <div className="global-page">
      <RegionalPanel onAlertClick={handleAlertClick} />
    </div>
  )
}
