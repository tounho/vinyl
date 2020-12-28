#include "pch.h"
#include "NotImplementedException.h"

NotImplementedException::NotImplementedException() : std::logic_error("Fuction not yet implemented.") { };
NotImplementedException::~NotImplementedException() { };
