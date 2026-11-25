// Nonthrowing log sink adapter;does not open configuration or log files.
package org.apache.logging.log4j;
@FunctionalInterface
public interface Logger {
    void warn(String message,Object first,Object second);
}
