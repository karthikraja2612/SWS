function QuestionChips({ questions, onQuestionClick, disabled }) {
  return (
    <section className="chips-wrap" aria-label="Suggested questions">
      <p className="chips-title">Try asking:</p>
      <div className="chips-grid">
        {questions.map((question) => (
          <button
            key={question}
            type="button"
            className="question-chip"
            onClick={() => onQuestionClick(question)}
            disabled={disabled}
          >
            {question}
          </button>
        ))}
      </div>
    </section>
  );
}

export default QuestionChips;
