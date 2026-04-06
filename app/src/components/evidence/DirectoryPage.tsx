import { useNavigate } from 'react-router-dom'
import DirectoryPanel from './DirectoryPanel'

export default function DirectoryPage() {
  const navigate = useNavigate()

  const handleCompanySearch = (name: string) => {
    navigate(`/?q=${encodeURIComponent(`What is ${name}'s pipeline and competitive landscape?`)}`)
  }

  return (
    <div className="directory-page">
      <DirectoryPanel onCompanySearch={handleCompanySearch} />
    </div>
  )
}
