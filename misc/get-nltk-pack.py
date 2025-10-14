from langchain_community.document_loaders import UnstructuredXMLLoader

loader = UnstructuredXMLLoader("/app/misc/dummy.xml")
loader.load_and_split()
