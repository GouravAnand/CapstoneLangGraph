Guidelines:
   
Overview:
Cease & Desist is a formal request from customers to stop all kinds of direct communication to them from the enterprise. The enterprise receives scanned PDF documents of customer requests. In current process, the human agents must then manually read the documents and figure out if that request is a "Cease" or "No Cease" request and then process it accordingly. The proposed solution automates this procedure.

Solution:
The solution shall classify incoming PDF documents in 3 categories - Requests for "Cease", "Uncertain - Manual review required" and "Irrelevant". If it's a "Cease" request, call an agent / tool that would write details to a datastore (Such as date of document received, document name). If "irrelevant", send to an archiving agent that writes to a flat file (Such as date of document received, document name). If uncertain, present it to a human agent. In all cases, log request (audit agent) with explanation for audit purposes.

Optionally, the solution should include the following.
    • Support multiple languages.
    • Dedicated agent to review/judge the output of categorization

Expected coverage from Participant's solution
    • Multiple agents
    • Human in the loop
    • Database interaction by agents
    • Auditing

Additional rationale required from Participant's solution
    • Citation behind how exactly the documents are categorized
    • Confidence score behind the categorization.
    • Edge case coverage
    • Why was this solution chosen over others
    • Solution scalability
    • Non Functional Requirements(NFR) implementation

Participant's Deliverable:
    • Presentation/deck covering the solution ( including expected coverage/additional rationale)
    • Code placed in a personal repo

Note: Please do not share any of the sample data/code/artifacts to Wells Fargo network.