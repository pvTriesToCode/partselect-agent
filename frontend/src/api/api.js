let conversationHistory = [];

export const getAIMessage = async (userQuery, onToken, onMetadata) => {
  try {
    const response = await fetch("http://localhost:8000/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: userQuery,
        history: conversationHistory,
      }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              fullContent += data.token;
              if (onToken) onToken(fullContent);
            }
            if (data.metadata) {
              if (onMetadata) onMetadata(data.metadata);
            }
            if (data.done) {
              conversationHistory = data.history;
            }
            if (data.error) {
              return {
                role: "assistant",
                content: "Sorry, I encountered an error. Please try again.",
              };
            }
          } catch (e) {
            // skip malformed lines
          }
        }
      }
    }

    return {
      role: "assistant",
      content: fullContent,
    };
  } catch (error) {
    return {
      role: "assistant",
      content: "Sorry, I could not connect to the server. Please make sure the backend is running.",
    };
  }
};

export const resetHistory = () => {
  conversationHistory = [];
};
