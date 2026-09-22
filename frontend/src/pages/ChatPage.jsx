import React, {
  useEffect,
  useRef,
  useState,
} from 'react';

import ChatBubble from '../components/ChatBubble';
import useSpeechRecognition from '../hooks/useSpeechRecognition';
import * as api from '../services/api';


/* =================================================================
   Constants
   ================================================================= */

const WELCOME_MESSAGE = {
  sender: 'bot',
  text:
    'Hello! I am your RAG Chatbot Assistant. Ask me anything about the files in your knowledge base.',
  timestamp: new Date().toISOString(),
};


/* =================================================================
   Main Component
   ================================================================= */

export default function ChatPage() {

  /* ----------------------------------------------------------------
     Conversation state
     ---------------------------------------------------------------- */

  const [
    conversationId,
    setConversationId,
  ] = useState(null);

  const [
    conversations,
    setConversations,
  ] = useState([]);

  const [
    loadingConversation,
    setLoadingConversation,
  ] = useState(true);

  const [
    conversationError,
    setConversationError,
  ] = useState(null);

  const [
    deletingConversationId,
    setDeletingConversationId,
  ] = useState(null);


  /* ----------------------------------------------------------------
     Chat state
     ---------------------------------------------------------------- */

  const [
    messages,
    setMessages,
  ] = useState([]);

  const [
    inputValue,
    setInputValue,
  ] = useState('');

  const [
    isTyping,
    setIsTyping,
  ] = useState(false);

  const [
    selectedSource,
    setSelectedSource,
  ] = useState(null);

  const [
    currentResults,
    setCurrentResults,
  ] = useState([]);


  /* ----------------------------------------------------------------
     Speech state
     ---------------------------------------------------------------- */

  const startTextRef =
    useRef('');

  const messagesContainerRef =
    useRef(null);


  /* =================================================================
     Speech Recognition
     ================================================================= */

  const handleSpeechResult =
    (transcript) => {
      setInputValue(
        startTextRef.current +
        (
          startTextRef.current &&
            transcript
            ? ' '
            : ''
        ) +
        transcript
      );
    };


  const {
    isListening,
    error: speechError,
    supported: speechSupported,
    startListening,
    stopListening,
    setError: setSpeechError,
  } = useSpeechRecognition({
    onResult:
      handleSpeechResult,
    lang: 'en-US',
  });


  /* =================================================================
     Scroll
     ================================================================= */

  const scrollToBottom = () => {
    const container = messagesContainerRef.current;

    if (!container) {
      return;
    }

    /*
     * Scroll the actual messages container instead of using
     * scrollIntoView() on a child element. This prevents the
     * outer .main-content container from being scrolled when
     * the ChatPage is remounted after switching pages.
     *
     * Use an instant scroll for restored conversations so the
     * browser does not animate through an old scroll position.
     */
    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'auto',
    });
  };


  useEffect(() => {
    scrollToBottom();
  }, [
    messages,
    isTyping,
  ]);


  /* =================================================================
     Helpers
     ================================================================= */

  const getSourceIdentifier =
    (source) => {

      if (!source) {
        return null;
      }

      if (
        typeof source === 'string'
      ) {
        return source;
      }

      return (
        source.chunk_id ||
        source.document_chunk_id ||
        source.id ||
        source.source ||
        null
      );
    };


  /*
   * Retrieval results can use the same identifier fields
   * as persisted source objects. Reuse the same matching
   * logic so Context Inspector can restore the full result
   * after a conversation is reopened.
   */
  const getResultIdentifier =
    (result) =>
      getSourceIdentifier(result);


  const isInsufficientContextAnswer =
    (text) => {

      if (typeof text !== 'string') {
        return false;
      }

      const normalized =
        text.toLowerCase();

      const refusalPatterns = [
        // Only match full no-evidence responses. A partial answer may
        // legitimately say that one part of the question is unsupported.
        'the retrieved documents do not contain any information',
        'retrieved documents do not contain any information',
        'the retrieved context does not contain any information',
        'retrieved context does not contain any information',
        'the available context does not contain any information',
        'the available context does not provide any information',
        'the context does not contain any information',
        "i don't have enough information in the available knowledge base",
        'i do not have enough information in the available knowledge base',
        'cannot answer from the available context',
        "can't answer from the available context",
        'no information is available in the retrieved context',
        'no information is available in the available context',
      ];

      return refusalPatterns.some(
        (pattern) => normalized.includes(pattern)
      );
    };


  const normalizeMessageMetadata =
    (metadata) => {

      if (!metadata) {
        return {};
      }

      if (
        typeof metadata === 'object'
      ) {
        return metadata;
      }

      if (
        typeof metadata === 'string'
      ) {
        try {
          const parsed =
            JSON.parse(metadata);

          return (
            parsed &&
            typeof parsed === 'object'
          )
            ? parsed
            : {};
        } catch {
          return {};
        }
      }

      return {};
    };


  /* =================================================================
     Convert backend message
     ================================================================= */

  const convertBackendMessage =
    (message) => {

      const metadata =
        normalizeMessageMetadata(
          message?.message_metadata
        );


      const text =
        message?.content || '';

      // Defensive cleanup for conversations created before the no-evidence
      // guard was added. Old persisted refusal messages may still contain
      // retrieval metadata, but that metadata should not populate the
      // Context Inspector because the answer explicitly says the context
      // did not contain the requested information.
      const isRefusal =
        isInsufficientContextAnswer(text);

      return {
        id: message?.id,

        sender:
          message?.role === 'user'
            ? 'user'
            : 'bot',

        text,

        timestamp:
          message?.created_at ||
          new Date().toISOString(),

        /*
         * Preserve all response information
         * needed by ChatBubble and the
         * Context Inspector.
         */
        sources:
          !isRefusal &&
          Array.isArray(
            metadata?.sources
          )
            ? metadata.sources
            : [],

        confidence:
          metadata?.confidence,

        speech_text:
          metadata?.speech_text ||
          null,

        retrieval_results:
          !isRefusal &&
          Array.isArray(
            metadata?.retrieval_results
          )
            ? metadata.retrieval_results
            : [],
      };
    };


  /* =================================================================
     Restore Context Inspector
     ================================================================= */

  const restoreInspectorFromMessages =
    (backendMessages) => {

      if (
        !Array.isArray(
          backendMessages
        ) ||
        backendMessages.length === 0
      ) {
        setCurrentResults([]);
        setSelectedSource(null);
        return;
      }


      /*
       * Find latest assistant response.
       */
      const latestAssistant =
        [...backendMessages]
          .reverse()
          .find(
            (message) =>
              message?.role ===
              'assistant'
          );


      if (!latestAssistant) {
        setCurrentResults([]);
        setSelectedSource(null);
        return;
      }


      const metadata =
        normalizeMessageMetadata(
          latestAssistant
            ?.message_metadata
        );


      const isRefusal =
        isInsufficientContextAnswer(
          latestAssistant?.content || ''
        );

      const results =
        !isRefusal &&
        Array.isArray(
          metadata?.retrieval_results
        )
          ? metadata.retrieval_results
          : [];


      const sources =
        !isRefusal &&
        Array.isArray(
          metadata?.sources
        )
          ? metadata.sources
          : [];


      setCurrentResults(
        results
      );


      if (results.length === 0) {
        setSelectedSource(null);
        return;
      }


      /*
       * Prefer a result referenced in sources.
       */
      const firstSource =
        sources.length > 0
          ? sources[0]
          : null;


      const sourceIdentifier =
        getSourceIdentifier(
          firstSource
        );


      let matchingResult =
        null;


      if (sourceIdentifier) {

        matchingResult =
          results.find(
            (result) => {

              const resultIdentifier =
                getResultIdentifier(result);

              return (
                String(
                  resultIdentifier
                ) ===
                String(
                  sourceIdentifier
                )
              );
            }
          ) || null;
      }


      /*
       * Fall back to the first retrieved
       * result when there is no direct match.
       */
      setSelectedSource(
        matchingResult ||
        results[0] ||
        null
      );
    };


  /* =================================================================
     Load one existing conversation
     ================================================================= */

  const loadConversation =
    async (
      selectedId
    ) => {

      if (!selectedId) {
        return;
      }


      setLoadingConversation(
        true
      );

      setConversationError(
        null
      );


      try {

        const conversation =
          await api.getConversation(
            selectedId
          );


        const backendMessages =
          Array.isArray(
            conversation?.messages
          )
            ? conversation.messages
            : [];


        setConversationId(
          selectedId
        );


        /*
         * Empty conversation:
         * keep it empty.
         */

        if (backendMessages.length === 0) {
          setMessages([
            {
              ...WELCOME_MESSAGE,
              timestamp: new Date().toISOString(),
            },
          ]);

          setCurrentResults([]);
          setSelectedSource(null);

          return;
        }

        const convertedMessages =
          backendMessages.map(
            convertBackendMessage
          );


        setMessages(
          convertedMessages
        );


        /*
         * Restore persisted sources.
         */
        restoreInspectorFromMessages(
          backendMessages
        );

      } catch (error) {

        console.error(
          'Failed to load conversation:',
          error
        );


        setConversationError(
          error?.message ||
          'Unable to load this conversation.'
        );


        setMessages([]);

        setCurrentResults([]);

        setSelectedSource(null);

      } finally {

        setLoadingConversation(
          false
        );
      }
    };


  /* =================================================================
     Load all conversations belonging to current user
     ================================================================= */

  const loadConversations =
    async () => {

      setLoadingConversation(
        true
      );

      setConversationError(
        null
      );


      try {

        const data =
          await api.getConversations();


        const userConversations =
          Array.isArray(
            data?.conversations
          )
            ? data.conversations
            : [];


        setConversations(
          userConversations
        );


        /*
         * IMPORTANT:
         *
         * Do NOT create an empty database
         * conversation when the ChatPage opens.
         */

        if (userConversations.length === 0) {
          setConversationId(null);

          setMessages([
            {
              ...WELCOME_MESSAGE,
              timestamp: new Date().toISOString(),
            },
          ]);

          setCurrentResults([]);
          setSelectedSource(null);

          return;
        }

        /*
         * Backend sorts conversations by
         * updated_at DESC.
         */
        const latestConversation =
          userConversations[0];


        const latestId =
          latestConversation
            ?.conversation_id;


        if (!latestId) {
          throw new Error(
            'Conversation ID is missing from the backend response.'
          );
        }


        await loadConversation(
          latestId
        );

      } catch (error) {

        console.error(
          'Failed to load conversations:',
          error
        );


        setConversationError(
          error?.message ||
          'Unable to load your conversation history.'
        );


        setConversationId(null);

        setMessages([]);

        setCurrentResults([]);

        setSelectedSource(null);

      } finally {

        setLoadingConversation(
          false
        );
      }
    };


  /* =================================================================
     Initial load
     ================================================================= */

  useEffect(() => {

    loadConversations();

    return () => {
      /*
       * Stop voice recognition when
       * leaving the page.
       */
      stopListening();

      if (
        'speechSynthesis' in
        window
      ) {
        window.speechSynthesis.cancel();
      }
    };

  }, []);


  /* =================================================================
     Select existing conversation
     ================================================================= */

  const handleSelectConversation =
    async (
      selectedId
    ) => {

      if (!selectedId) {
        return;
      }


      if (
        selectedId ===
        conversationId
      ) {
        return;
      }


      /*
       * Stop speech recognition before
       * switching conversations.
       */
      if (isListening) {
        stopListening();
      }


      await loadConversation(
        selectedId
      );
    };


  /* =================================================================
     Delete Conversation
     ================================================================= */

  const handleDeleteConversation =
    async (conversationToDelete) => {

      if (!conversationToDelete) {
        return;
      }

      const idToDelete =
        conversationToDelete.conversation_id;

      if (!idToDelete || deletingConversationId) {
        return;
      }

      const confirmed = window.confirm(
        'Are you sure you want to delete this conversation? This action cannot be undone.'
      );

      if (!confirmed) {
        return;
      }

      if (isListening) {
        stopListening();
      }

      if (
        'speechSynthesis' in
        window
      ) {
        window.speechSynthesis.cancel();
      }

      setDeletingConversationId(idToDelete);
      setConversationError(null);

      try {

        await api.deleteConversation(
          idToDelete
        );

        const remainingConversations =
          conversations.filter(
            (conversation) =>
              conversation.conversation_id !==
              idToDelete
          );

        setConversations(
          remainingConversations
        );

        /*
         * If another conversation is currently
         * open, leave it untouched.
         */
        if (conversationId !== idToDelete) {
          return;
        }

        /*
         * The active conversation was deleted.
         * Open the next available conversation.
         * If none remain, start a clean local chat.
         */
        if (remainingConversations.length > 0) {

          const nextConversation =
            remainingConversations[0];

          await loadConversation(
            nextConversation.conversation_id
          );

        } else {

          setConversationId(null);

          setMessages([
            {
              ...WELCOME_MESSAGE,
              timestamp: new Date().toISOString(),
            },
          ]);

          setCurrentResults([]);
          setSelectedSource(null);
          setInputValue('');
        }

      } catch (error) {

        console.error(
          'Failed to delete conversation:',
          error
        );

        setConversationError(
          error?.message ||
          'Unable to delete this conversation. Please try again.'
        );

      } finally {

        setDeletingConversationId(null);
      }
    };


  /* =================================================================
     New Chat
     ================================================================= */

  const handleNewConversation =
    () => {

      /*
       * IMPORTANT:
       *
       * Do not immediately call
       * POST /conversations.
       *
       * This only creates a new local
       * chat state. The backend conversation
       * is created when the first real
       * message is sent.
       */
      if (isListening) {
        stopListening();
      }


      if (
        'speechSynthesis' in
        window
      ) {
        window.speechSynthesis.cancel();
      }

      setConversationId(null);

      setMessages([
        {
          ...WELCOME_MESSAGE,
          timestamp: new Date().toISOString(),
        },
      ]);

      setCurrentResults([]);

      setSelectedSource(null);

      setConversationError(null);

      setInputValue('');
    };


  /* =================================================================
     Ensure backend conversation exists
     ================================================================= */

  const ensureConversation =
    async () => {

      /*
       * Existing persistent conversation.
       */
      if (conversationId) {
        return conversationId;
      }


      /*
       * Create the conversation only when
       * the user actually sends the first message.
       */
      const created =
        await api.createConversation();


      const newId =
        created?.conversation_id;


      if (!newId) {
        throw new Error(
          'The backend did not return a conversation ID.'
        );
      }


      setConversationId(
        newId
      );


      /*
       * Add it to local dropdown.
       */
      setConversations(
        (previous) => [
          {
            conversation_id:
              newId,

            created_at:
              created?.created_at ||
              new Date().toISOString(),

            updated_at:
              created?.updated_at ||
              new Date().toISOString(),
          },

          ...previous,
        ]
      );


      return newId;
    };


  /* =================================================================
     Microphone
     ================================================================= */

  const handleMicClick =
    () => {

      if (!speechSupported) {

        setSpeechError(
          'Speech recognition is not supported in this browser. Please use a supported browser or type your question.'
        );

        return;
      }


      if (isListening) {

        stopListening();

      } else {

        /*
         * Save existing typed text so
         * speech can be appended to it.
         */
        startTextRef.current =
          inputValue;


        setSpeechError(null);

        startListening();
      }
    };


  /* =================================================================
     Send message
     ================================================================= */

  const handleSend =
    async (
      textToSend
    ) => {

      /*
       * Stop voice recognition.
       */
      if (isListening) {
        stopListening();
      }


      /*
       * Stop TTS/Read Aloud.
       *
       * This preserves the existing behavior.
       */
      if (
        'speechSynthesis' in
        window
      ) {
        window.speechSynthesis.cancel();
      }


      const text =
        (
          textToSend ||
          inputValue
        ).trim();

      console.log("[CHAT] Current user question:", text);

      if (!text || isTyping) {
        return;
      }


      if (!textToSend) {
        setInputValue('');
      }


      setConversationError(
        null
      );


      /*
       * Snapshot previous history
       * before adding current message.
       */
      const history =
        messages.map(
          (message) => ({
            role:
              message.sender ===
                'user'
                ? 'user'
                : 'assistant',

            content:
              message.text,
          })
        );


      /*
       * Show user message immediately.
       */
      const userMessage = {
        sender: 'user',
        text,
        timestamp:
          new Date().toISOString(),
      };


      setMessages(
        (previous) => [
          ...previous,
          userMessage,
        ]
      );


      setIsTyping(true);


      try {

        /*
         * Create persistent backend conversation
         * if this is a brand-new chat.
         */
        const activeConversationId =
          await ensureConversation();


        /*
         * Send query with persistent UUID.
         */
        const response =
          await api.sendChatMessage(
            text,
            history,
            activeConversationId
          );


        /* ----------------------------------------------------------
           Clarification response
           ---------------------------------------------------------- */

        if (
          response?.clarification_required
        ) {

          const clarificationQuestion =
            response?.clarification_question ||
            'Could you please clarify your question?';


          const clarificationMessage = {
            sender: 'bot',

            text:
              clarificationQuestion,

            timestamp:
              new Date().toISOString(),

            sources: [],

            retrieval_results: [],
          };


          setMessages(
            (previous) => [
              ...previous,
              clarificationMessage,
            ]
          );


          setCurrentResults([]);

          setSelectedSource(null);


          return;
        }


        /* ----------------------------------------------------------
           Normal RAG response
           ---------------------------------------------------------- */

        const answer =
          response?.response?.answer ||
          'I could not generate an answer from the available knowledge base.';


        const sources =
          Array.isArray(
            response?.response?.sources
          )
            ? response.response.sources
            : [];


        const results =
          Array.isArray(
            response?.retrieval?.results
          )
            ? response.retrieval.results
            : [];


        /*
         * This object contains everything needed
         * immediately AND after rendering.
         *
         * The backend separately persists this
         * information through message_metadata.
         */
        const botMessage = {
          sender: 'bot',

          text:
            answer,

          speech_text:
            response?.speech_text ||
            null,

          sources,

          confidence:
            response?.response?.confidence,

          retrieval_results:
            results,

          timestamp:
            new Date().toISOString(),
        };


        setMessages(
          (previous) => [
            ...previous,
            botMessage,
          ]
        );


        /* ----------------------------------------------------------
           Context Inspector
           ---------------------------------------------------------- */

        setCurrentResults(
          results
        );


        if (
          results.length > 0
        ) {

          const firstSource =
            sources.length > 0
              ? sources[0]
              : null;


          const sourceIdentifier =
            getSourceIdentifier(
              firstSource
            );


          let selected =
            null;


          if (sourceIdentifier) {

            selected =
              results.find(
                (result) => {

                  const resultIdentifier =
                    getResultIdentifier(result);

                  return (
                    String(
                      resultIdentifier
                    ) ===
                    String(
                      sourceIdentifier
                    )
                  );
                }
              ) || null;
          }


          setSelectedSource(
            selected ||
            results[0] ||
            null
          );

        } else {

          setSelectedSource(
            null
          );
        }


        /* ----------------------------------------------------------
           Refresh conversation list
           ---------------------------------------------------------- */

        try {

          const conversationData =
            await api.getConversations();


          if (
            Array.isArray(
              conversationData?.conversations
            )
          ) {

            setConversations(
              conversationData.conversations
            );
          }

        } catch (listError) {

          console.warn(
            'Could not refresh conversation list:',
            listError
          );
        }

      } catch (error) {

        console.error(
          'Query failed:',
          error
        );


        const errorMessage = {
          sender: 'bot',

          text:
            error?.message ||
            'I’m sorry, but I couldn’t process your request. Please try again.',

          timestamp:
            new Date().toISOString(),

          sources: [],

          retrieval_results: [],
        };


        setMessages(
          (previous) => [
            ...previous,
            errorMessage,
          ]
        );


        setCurrentResults([]);

        setSelectedSource(null);

      } finally {

        setIsTyping(false);
      }
    };


  /* =================================================================
     Keyboard
     ================================================================= */

  const handleKeyDown =
    (event) => {

      if (
        event.key === 'Enter' &&
        !event.shiftKey
      ) {

        event.preventDefault();

        handleSend();
      }
    };


  /* =================================================================
     Source selection
     ================================================================= */

  const handleSelectSource =
    (source, message) => {

      if (!source) {
        return;
      }


      /*
       * IMPORTANT:
       * A source belongs to the assistant message that rendered it.
       * Do not use the global currentResults here because that state
       * represents the most recently active retrieval set, not
       * necessarily the retrieval set for the source being clicked.
       *
       * Using the message's own retrieval_results keeps the Context
       * Inspector scoped to the historical response the user clicked.
       */
      const messageResults =
        Array.isArray(
          message?.retrieval_results
        )
          ? message.retrieval_results
          : [];


      /*
       * Keep the inspector's "All Matches" list synchronized with
       * the message whose source was selected.
       */
      setCurrentResults(
        messageResults
      );


      const sourceIdentifier =
        getSourceIdentifier(
          source
        );


      /*
       * Match by chunk ID first.
       */
      if (
        sourceIdentifier &&
        messageResults.length > 0
      ) {

        const matchingResult =
          messageResults.find(
            (result) => {

              const resultIdentifier =
                getResultIdentifier(result);

              return (
                String(
                  resultIdentifier
                ) ===
                String(
                  sourceIdentifier
                )
              );
            }
          );


        if (matchingResult) {

          setSelectedSource(
            matchingResult
          );

          return;
        }
      }


      /*
       * Filename fallback.
       */
      const sourceFilename =
        source?.metadata?.filename ||
        source?.filename ||
        source?.document ||
        null;


      if (
        sourceFilename &&
        messageResults.length > 0
      ) {

        const filenameMatch =
          messageResults.find(
            (result) =>
              result?.metadata?.filename ===
              sourceFilename
          );


        if (filenameMatch) {

          setSelectedSource(
            filenameMatch
          );

          return;
        }
      }


      /*
       * Final fallback.
       *
       * This preserves the previous behavior for source objects that
       * already contain their own inspector data.
       */
      setSelectedSource(
        source
      );
    };


  /* =================================================================
     Render
     ================================================================= */

  return (
    <div
      className="chat-page-layout"
      style={{
        display: 'flex',
        width: '100%',
        height: '100%',
        minHeight: 0,
        overflow: 'hidden',
      }}
    >

      {/* ============================================================
          LEFT CHAT PANEL
          ============================================================ */}

      <div
        className="chat-page-main-panel"
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          minHeight: 0,
          borderRight:
            '1px solid var(--border-color)',
          position: 'relative',
          minWidth: 0,
        }}
      >

        {/* ----------------------------------------------------------
            Header
            ---------------------------------------------------------- */}

        <div
          style={{
            padding:
              '16px 32px',
            borderBottom:
              '1px solid var(--border-color)',
            display: 'flex',
            justifyContent:
              'space-between',
            alignItems:
              'center',
            gap: '15px',
          }}
        >

          <div
            style={{
              textAlign: 'left',
              minWidth: 0,
            }}
          >

            <h2
              style={{
                fontSize:
                  '1.25rem',
                fontWeight: 600,
                margin: 0,
              }}
            >
              AI Assistant
            </h2>


            <p
              style={{
                fontSize:
                  '0.8rem',
                color:
                  'var(--text-muted)',
                margin:
                  '4px 0 0',
              }}
            >
              Retrieval-Augmented Chat Engine
            </p>

          </div>


          <button
            type="button"
            onClick={
              handleNewConversation
            }
            disabled={
              loadingConversation ||
              isTyping
            }
            className="btn btn-secondary"
            style={{
              fontSize:
                '0.8rem',
              padding:
                '6px 12px',
              flexShrink: 0,
            }}
          >
            New Chat
          </button>

        </div>


        {/* ----------------------------------------------------------
            Conversation selector
            ---------------------------------------------------------- */}

        {conversations.length > 0 && (
          <div
            style={{
              padding:
                '10px 32px',
              borderBottom:
                '1px solid var(--border-color)',
              background:
                'var(--bg-surface-opaque)',
            }}
          >

            <div
              style={{
                width: '100%',
                maxWidth: '680px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >

              <select
                value={
                  conversationId ||
                  ''
                }
                onChange={
                  (event) =>
                    handleSelectConversation(
                      event.target.value
                    )
                }
                disabled={
                  loadingConversation ||
                  isTyping ||
                  Boolean(deletingConversationId)
                }
                style={{
                  flex: 1,
                  minWidth: 0,
                  height: '38px',
                  padding: '0 12px',
                  borderRadius: '9px',
                  border:
                    '1px solid var(--border-color)',
                  background: 'var(--bg-input)',
                  color: 'var(--text-secondary)',
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >

                {conversations.map(
                  (
                    conversation,
                    index
                  ) => (

                    <option
                      key={
                        conversation.conversation_id
                      }
                      value={
                        conversation.conversation_id
                      }
                    >
                      {conversation.title?.trim() ||
                        `Conversation ${conversations.length -
                        index
                        }`}
                    </option>

                  )
                )}

              </select>

              <button
                type="button"
                onClick={() => {
                  const selectedConversation =
                    conversations.find(
                      (conversation) =>
                        conversation.conversation_id ===
                        conversationId
                    );

                  handleDeleteConversation(
                    selectedConversation
                  );
                }}
                disabled={
                  loadingConversation ||
                  isTyping ||
                  !conversationId ||
                  Boolean(deletingConversationId)
                }
                title="Delete conversation"
                aria-label="Delete conversation"
                style={{
                  width: '38px',
                  height: '38px',
                  flexShrink: 0,
                  borderRadius: '9px',
                  border:
                    '1px solid var(--border-color)',
                  background: 'var(--bg-input)',
                  color: 'var(--accent-rose)',
                  cursor:
                    loadingConversation ||
                      isTyping ||
                      !conversationId ||
                      deletingConversationId
                      ? 'not-allowed'
                      : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity:
                    loadingConversation ||
                      isTyping ||
                      !conversationId ||
                      deletingConversationId
                      ? 0.5
                      : 1,
                }}
              >

                {deletingConversationId === conversationId ? (
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 600,
                    }}
                  >
                    ...
                  </span>
                ) : (
                  <svg
                    width="17"
                    height="17"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    <line x1="10" y1="11" x2="10" y2="17" />
                    <line x1="14" y1="11" x2="14" y2="17" />
                  </svg>
                )}

              </button>

            </div>

          </div>
        )}


        {/* ----------------------------------------------------------
            Loading
            ---------------------------------------------------------- */}

        {loadingConversation && (
          <div
            style={{
              padding:
                '8px 32px',
              fontSize:
                '0.72rem',
              color:
                'var(--text-muted)',
            }}
          >
            Loading conversation history...
          </div>
        )}


        {/* ----------------------------------------------------------
            Conversation error
            ---------------------------------------------------------- */}

        {conversationError && (
          <div
            style={{
              margin:
                '10px 32px 0',
              padding:
                '9px 12px',
              borderRadius:
                '8px',
              border:
                '1px solid rgba(255, 80, 80, 0.18)',
              background:
                'rgba(255, 80, 80, 0.06)',
              color:
                '#ff9999',
              fontSize:
                '0.75rem',
              textAlign:
                'left',
            }}
          >
            {conversationError}
          </div>
        )}


        {/* ----------------------------------------------------------
            Empty new-chat state
            ---------------------------------------------------------- */}

        {!loadingConversation &&
          messages.length === 0 && (
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems:
                  'center',
                justifyContent:
                  'center',
                padding:
                  '32px',
                textAlign:
                  'center',
                color:
                  'var(--text-muted)',
              }}
            >

              <div
                style={{
                  maxWidth:
                    '520px',
                }}
              >

                <div
                  style={{
                    width:
                      '58px',
                    height:
                      '58px',
                    margin:
                      '0 auto 16px',
                    borderRadius:
                      '16px',
                    display:
                      'flex',
                    alignItems:
                      'center',
                    justifyContent:
                      'center',
                    background:
                      'hsla(185, 100%, 48%, 0.08)',
                    border:
                      '1px solid hsla(185, 100%, 48%, 0.14)',
                  }}
                >

                  <svg
                    width="28"
                    height="28"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>

                </div>


                <h3
                  style={{
                    color:
                      'var(--text-secondary)',
                    margin:
                      '0 0 8px',
                    fontSize:
                      '1.05rem',
                  }}
                >
                  Start a new conversation
                </h3>


                <p
                  style={{
                    margin:
                      0,
                    fontSize:
                      '0.82rem',
                    lineHeight:
                      '1.5',
                  }}
                >
                  Ask a question about your
                  indexed documents. Your
                  conversation will be saved
                  automatically.
                </p>

              </div>

            </div>
          )}


        {/* ----------------------------------------------------------
            Messages
            ---------------------------------------------------------- */}

        {messages.length > 0 && (
          <div
            ref={messagesContainerRef}
            style={{
              flex: 1,
              minHeight: 0,
              overflowY:
                'auto',
              padding:
                '32px',
              display:
                'flex',
              flexDirection:
                'column',
            }}
          >

            {messages.map(
              (
                message,
                index
              ) => (

                <ChatBubble
                  key={
                    message.id ||
                    `${message.timestamp}-${index}`
                  }
                  message={
                    message
                  }
                  onSelectSource={
                    handleSelectSource
                  }
                />

              )
            )}


            {/* Typing indicator */}

            {isTyping && (
              <div
                style={{
                  display:
                    'flex',
                  flexDirection:
                    'column',
                  alignItems:
                    'flex-start',
                  marginBottom:
                    '20px',
                }}
              >

                <div
                  style={{
                    display:
                      'flex',
                    alignItems:
                      'center',
                    gap:
                      '6px',
                    marginBottom:
                      '6px',
                    fontSize:
                      '0.8rem',
                    color:
                      'var(--text-muted)',
                  }}
                >

                  <span
                    style={{
                      fontWeight:
                        600,
                    }}
                  >
                    AI Assistant
                  </span>

                  <span>
                    •
                  </span>

                  <span>
                    Thinking...
                  </span>

                </div>


                <div
                  className="glass-card"
                  style={{
                    padding:
                      '12px 18px',
                    borderRadius:
                      '16px 16px 16px 4px',
                    background:
                      'var(--bg-surface)',
                    border:
                      '1px solid var(--border-color)',
                  }}
                >

                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />

                </div>

              </div>
            )}

          </div>
        )}


        {/* ----------------------------------------------------------
            Input area
            ---------------------------------------------------------- */}

        <div
          style={{
            padding:
              '24px 32px 32px',
            borderTop:
              '1px solid var(--border-color)',
            background:
              'var(--bg-surface-opaque)',
          }}
        >

          {/* Speech error */}

          {speechError && (
            <div
              style={{
                padding:
                  '10px 16px',
                background:
                  'hsla(0, 85%, 60%, 0.1)',
                border:
                  '1px solid var(--accent-rose)',
                borderRadius:
                  '8px',
                color:
                  'var(--accent-rose)',
                fontSize:
                  '0.8rem',
                marginBottom:
                  '12px',
                display:
                  'flex',
                justifyContent:
                  'space-between',
                alignItems:
                  'center',
                textAlign:
                  'left',
              }}
            >

              <span
                style={{
                  display:
                    'flex',
                  alignItems:
                    'center',
                  gap:
                    '8px',
                }}
              >

                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                  />

                  <line
                    x1="12"
                    y1="8"
                    x2="12"
                    y2="12"
                  />

                  <line
                    x1="12"
                    y1="16"
                    x2="12.01"
                    y2="16"
                  />
                </svg>

                {speechError}

              </span>


              <button
                type="button"
                onClick={() =>
                  setSpeechError(null)
                }
                style={{
                  background:
                    'transparent',
                  border:
                    'none',
                  color:
                    'var(--accent-rose)',
                  cursor:
                    'pointer',
                  fontSize:
                    '1.2rem',
                  fontWeight:
                    'bold',
                  lineHeight:
                    '1',
                  padding:
                    '0 4px',
                  display:
                    'flex',
                  alignItems:
                    'center',
                }}
                aria-label="Dismiss error"
              >
                ×
              </button>

            </div>
          )}


          <div
            style={{
              display:
                'flex',
              gap:
                '12px',
              position:
                'relative',
              alignItems:
                'center',
            }}
          >

            {/* ======================================================
                Textarea
                ====================================================== */}

            <textarea
              className="input-text"
              value={
                inputValue
              }
              onChange={
                (event) =>
                  setInputValue(
                    event.target.value
                  )
              }
              onKeyDown={
                handleKeyDown
              }
              placeholder="Ask a question about your uploaded documents..."
              rows="1"
              disabled={
                loadingConversation ||
                isTyping
              }
              style={{
                resize:
                  'none',
                height:
                  '50px',
                paddingTop:
                  '14px',
                paddingRight:
                  '92px',
                lineHeight:
                  '1.4',
              }}
            />


            {/* ======================================================
                Microphone
                ====================================================== */}

            <button
              type="button"
              onClick={
                handleMicClick
              }
              disabled={
                loadingConversation ||
                isTyping
              }
              className={`btn ${isListening
                  ? 'btn-secondary'
                  : ''
                }`}
              title={
                isListening
                  ? 'Stop listening'
                  : 'Start voice input'
              }
              aria-label={
                isListening
                  ? 'Stop listening'
                  : 'Start voice input'
              }
              style={{
                position:
                  'absolute',
                right:
                  '48px',
                height:
                  '38px',
                width:
                  '38px',
                borderRadius:
                  '8px',
                padding:
                  0,
                display:
                  'flex',
                alignItems:
                  'center',
                justifyContent:
                  'center',
                background:
                  isListening
                    ? 'var(--accent-rose)'
                    : 'var(--bg-card)',
                color:
                  isListening
                    ? '#ffffff'
                    : 'var(--text-primary)',
                border:
                  '1px solid ' +
                  (
                    isListening
                      ? 'var(--accent-rose)'
                      : 'var(--border-color)'
                  ),
                animation:
                  isListening
                    ? 'pulse-glow 1.5s infinite'
                    : 'none',
                cursor:
                  (
                    loadingConversation ||
                    isTyping
                  )
                    ? 'not-allowed'
                    : 'pointer',
              }}
            >

              {isListening ? (

                /* Stop */

                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect
                    x="4"
                    y="4"
                    width="16"
                    height="16"
                    rx="2"
                  />
                </svg>

              ) : (

                /* Microphone */

                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />

                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />

                  <line
                    x1="12"
                    y1="19"
                    x2="12"
                    y2="23"
                  />

                  <line
                    x1="8"
                    y1="23"
                    x2="16"
                    y2="23"
                  />
                </svg>

              )}

            </button>


            {/* ======================================================
                Send
                ====================================================== */}

            <button
              type="button"
              onClick={() =>
                handleSend()
              }
              disabled={
                !inputValue.trim() ||
                isTyping ||
                loadingConversation
              }
              className="btn btn-primary"
              style={{
                position:
                  'absolute',
                right:
                  '6px',
                height:
                  '38px',
                width:
                  '38px',
                borderRadius:
                  '8px',
                padding:
                  0,
                display:
                  'flex',
                alignItems:
                  'center',
                justifyContent:
                  'center',
              }}
            >

              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >

                <line
                  x1="22"
                  y1="2"
                  x2="11"
                  y2="13"
                />

                <polygon
                  points="22 2 15 22 11 13 2 9 22 2"
                />

              </svg>

            </button>

          </div>


          {/* Listening status */}

          {isListening ? (

            <div
              style={{
                marginTop:
                  '12px',
                textAlign:
                  'center',
                fontSize:
                  '0.75rem',
                color:
                  'var(--accent-rose)',
                display:
                  'flex',
                alignItems:
                  'center',
                justifyContent:
                  'center',
                gap:
                  '6px',
              }}
            >

              <span
                style={{
                  display:
                    'inline-block',
                  width:
                    '8px',
                  height:
                    '8px',
                  borderRadius:
                    '50%',
                  background:
                    'var(--accent-rose)',
                  animation:
                    'pulse-glow 1.5s infinite',
                }}
              />

              Listening... Speak now.

            </div>

          ) : (

            <div
              style={{
                marginTop:
                  '12px',
                textAlign:
                  'center',
                fontSize:
                  '0.75rem',
                color:
                  'var(--text-muted)',
              }}
            >
              AI Assistant will search and answer based on your indexed knowledge base documents.
            </div>

          )}

        </div>

      </div>


      {/* ============================================================
          CONTEXT INSPECTOR
          ============================================================ */}

      <div
        className="context-inspector-panel"
        style={{
          width:
            '360px',
          height:
            '100%',
          display:
            'flex',
          flexDirection:
            'column',
          background:
            'var(--bg-surface-opaque)',
          flexShrink:
            0,
        }}
      >

        {/* ----------------------------------------------------------
            Inspector header
            ---------------------------------------------------------- */}

        <div
          style={{
            padding:
              '20px 24px',
            borderBottom:
              '1px solid var(--border-color)',
            textAlign:
              'left',
          }}
        >

          <h3
            style={{
              fontSize:
                '1.1rem',
              fontWeight:
                600,
              margin:
                0,
            }}
          >
            Context Inspector
          </h3>


          <p
            style={{
              fontSize:
                '0.75rem',
              color:
                'var(--text-muted)',
              margin:
                '5px 0 0',
            }}
          >
            Semantic matches retrieved from Database
          </p>

        </div>


        {/* ----------------------------------------------------------
            Inspector content
            ---------------------------------------------------------- */}

        <div
          style={{
            flex:
              1,
            overflowY:
              'auto',
            padding:
              '20px',
            display:
              'flex',
            flexDirection:
              'column',
            gap:
              '16px',
          }}
        >

          {!selectedSource ? (

            <div
              style={{
                display:
                  'flex',
                flexDirection:
                  'column',
                alignItems:
                  'center',
                justifyContent:
                  'center',
                height:
                  '100%',
                color:
                  'var(--text-muted)',
                textAlign:
                  'center',
                padding:
                  '20px',
              }}
            >

              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{
                  marginBottom:
                    '12px',
                }}
              >

                <circle
                  cx="11"
                  cy="11"
                  r="8"
                />

                <line
                  x1="21"
                  y1="21"
                  x2="16.65"
                  y2="16.65"
                />

              </svg>


              <h4
                style={{
                  fontSize:
                    '0.9rem',
                  marginBottom:
                    '4px',
                }}
              >
                No Source Selected
              </h4>


              <p
                style={{
                  fontSize:
                    '0.75rem',
                  margin:
                    0,
                }}
              >
                Ask a question first, then click on a source pill to inspect its raw text chunk.
              </p>

            </div>

          ) : (

            <div
              className="animate-fade-in"
              style={{
                textAlign:
                  'left',
              }}
            >

              {/* ----------------------------------------------------
                  Document details
                  ---------------------------------------------------- */}

              <div
                className="glass-card"
                style={{
                  padding:
                    '16px',
                  border:
                    '1px solid var(--border-color)',
                  borderRadius:
                    '10px',
                  marginBottom:
                    '16px',
                }}
              >

                <div
                  style={{
                    display:
                      'flex',
                    alignItems:
                      'center',
                    gap:
                      '10px',
                    marginBottom:
                      '8px',
                  }}
                >

                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{
                      color:
                        'var(--accent-purple)',
                    }}
                  >

                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />

                    <polyline
                      points="14 2 14 8 20 8"
                    />

                  </svg>


                  <span
                    style={{
                      fontSize:
                        '0.85rem',
                      fontWeight:
                        600,
                      wordBreak:
                        'break-all',
                    }}
                  >
                    {
                      selectedSource?.metadata?.filename ||
                      selectedSource?.filename ||
                      selectedSource?.document ||
                      selectedSource?.source ||
                      'Retrieved document'
                    }
                  </span>

                </div>


                <div
                  style={{
                    display:
                      'flex',
                    justifyContent:
                      'space-between',
                    gap:
                      '10px',
                    fontSize:
                      '0.75rem',
                    color:
                      'var(--text-muted)',
                  }}
                >

                  <span>
                    Chunk ID:{' '}

                    <strong>
                      {
                        selectedSource?.chunk_id ||
                        selectedSource?.id ||
                        'Unavailable'
                      }
                    </strong>
                  </span>


                  <span>
                    Relevance:{' '}

                    <strong
                      style={{
                        color:
                          'var(--accent-emerald)',
                      }}
                    >
                      {Math.round(
                        Number(
                          selectedSource?.relevance_score ||
                          0
                        ) * 100
                      )}
                      %
                    </strong>
                  </span>

                </div>

              </div>


              {/* ----------------------------------------------------
                  Retrieved chunk
                  ---------------------------------------------------- */}

              <h4
                style={{
                  fontSize:
                    '0.85rem',
                  fontWeight:
                    600,
                  color:
                    'var(--text-secondary)',
                  marginBottom:
                    '8px',
                  textTransform:
                    'uppercase',
                  letterSpacing:
                    '0.05em',
                }}
              >
                Retrieved Context Chunk
              </h4>


              <div
                className="glass-card"
                style={{
                  padding:
                    '16px',
                  fontSize:
                    '0.85rem',
                  lineHeight:
                    '1.5',
                  fontFamily:
                    'var(--font-mono)',
                  background:
                    'var(--bg-input)',
                  border:
                    '1px solid var(--border-color)',
                  borderRadius:
                    '8px',
                  color:
                    'var(--text-secondary)',
                  maxHeight:
                    '260px',
                  overflowY:
                    'auto',
                  whiteSpace:
                    'pre-wrap',
                }}
              >
                {
                  selectedSource?.content ||
                  'No retrieved content is available for this source.'
                }
              </div>


              {/* ----------------------------------------------------
                  Metrics
                  ---------------------------------------------------- */}

              <div
                style={{
                  display:
                    'flex',
                  gap:
                    '12px',
                  fontSize:
                    '0.75rem',
                  color:
                    'var(--text-muted)',
                  marginTop:
                    '10px',
                  flexWrap:
                    'wrap',
                }}
              >

                <span>
                  Semantic:{' '}

                  <strong>
                    {Number(
                      selectedSource?.semantic_score ||
                      0
                    ).toFixed(3)}
                  </strong>
                </span>


                <span>
                  Metadata:{' '}

                  <strong>
                    {
                      Object.keys(
                        selectedSource?.metadata ||
                        {}
                      ).length
                    }{' '}
                    fields
                  </strong>
                </span>

              </div>


              {/* ----------------------------------------------------
                  All retrieved matches
                  ---------------------------------------------------- */}

              {currentResults.length >
                0 && (

                  <div
                    style={{
                      marginTop:
                        '24px',
                    }}
                  >

                    <h4
                      style={{
                        fontSize:
                          '0.85rem',
                        fontWeight:
                          600,
                        color:
                          'var(--text-secondary)',
                        marginBottom:
                          '10px',
                        textTransform:
                          'uppercase',
                        letterSpacing:
                          '0.05em',
                      }}
                    >
                      All Matches (
                      {
                        currentResults.length
                      }
                      )
                    </h4>


                    <div
                      style={{
                        display:
                          'flex',
                        flexDirection:
                          'column',
                        gap:
                          '8px',
                      }}
                    >

                      {currentResults.map(
                        (
                          source,
                          index
                        ) => {

                          const sourceId =
                            source?.chunk_id ||
                            source?.document_chunk_id ||
                            source?.id ||
                            source?.source ||
                            `result-${index}`;


                          const selectedId =
                            selectedSource?.chunk_id ||
                            selectedSource?.document_chunk_id ||
                            selectedSource?.id ||
                            selectedSource?.source ||
                            null;

                          // When the retrieved records contain duplicate or
                          // fallback identifiers (for example the same
                          // filename), use object identity for the current
                          // result set so only the clicked chunk is selected.
                          const selectedIsCurrentResult =
                            currentResults.includes(
                              selectedSource
                            );

                          const isSelected =
                            selectedIsCurrentResult
                              ? source === selectedSource
                              : (
                                  selectedId !== null &&
                                  String(
                                    selectedId
                                  ) ===
                                  String(
                                    sourceId
                                  )
                                );


                          return (
                            <div
                              key={
                                `${sourceId}-${index}`
                              }
                              onClick={() =>
                                setSelectedSource(
                                  source
                                )
                              }
                              style={{
                                padding:
                                  '10px 12px',
                                borderRadius:
                                  '8px',
                                border:
                                  '1px solid ' +
                                  (
                                    isSelected
                                      ? 'var(--accent-purple)'
                                      : 'var(--border-color)'
                                  ),
                                background:
                                  isSelected
                                    ? 'hsla(263, 85%, 65%, 0.08)'
                                    : 'transparent',
                                cursor:
                                  'pointer',
                                display:
                                  'flex',
                                justifyContent:
                                  'space-between',
                                alignItems:
                                  'center',
                                fontSize:
                                  '0.75rem',
                                gap:
                                  '10px',
                              }}
                            >

                              <span
                                style={{
                                  overflow:
                                    'hidden',
                                  textOverflow:
                                    'ellipsis',
                                  whiteSpace:
                                    'nowrap',
                                  maxWidth:
                                    '210px',
                                }}
                              >

                                {
                                  source?.metadata?.filename ||
                                  source?.filename ||
                                  'Retrieved document'
                                }

                                <span
                                  style={{
                                    color:
                                      'var(--text-muted)',
                                  }}
                                >
                                  {' '}
                                  [
                                  {
                                    source?.chunk_id ||
                                    source?.id ||
                                    'chunk'
                                  }
                                  ]
                                </span>

                              </span>


                              <span
                                style={{
                                  fontWeight:
                                    'bold',
                                  color:
                                    'var(--accent-emerald)',
                                }}
                              >
                                {Math.round(
                                  Number(
                                    source?.relevance_score ||
                                    0
                                  ) * 100
                                )}
                                %
                              </span>

                            </div>
                          );
                        }
                      )}

                    </div>

                  </div>
                )}

            </div>
          )}

        </div>

      </div>

    </div>
  );
}
