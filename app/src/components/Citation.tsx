import { useCitation } from '../context/CitationContext';

interface CitationProps {
  section: string;
  number: number;
}

export default function Citation({ section, number }: CitationProps) {
  const { getCitationByNumber, openSource } = useCitation();

  const citation = getCitationByNumber(section, number);

  const handleClick = () => {
    if (citation) {
      openSource(citation);
    }
  };

  // If no citation exists for this number, render nothing
  if (!citation) {
    return null;
  }

  return (
    <button
      onClick={handleClick}
      className="citation-link"
      title={citation.source.title}
    >
      [{number}]
    </button>
  );
}
